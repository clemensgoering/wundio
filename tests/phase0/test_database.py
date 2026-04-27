"""
tests/phase0/test_database.py – Settings helpers and log_event cap behaviour.
"""
from database import MAX_EVENTS


class TestDatabase:
    def test_set_and_get_setting(self, tmp_db):
        from database import set_setting, get_setting
        set_setting("test_key", "hello")
        assert get_setting("test_key") == "hello"

    def test_get_missing_returns_falsy(self, tmp_db):
        from database import get_setting
        result = get_setting("nonexistent")
        assert not result, f"Expected falsy for missing key, got {result!r}"

    def test_log_event_does_not_raise(self, tmp_db):
        from database import log_event
        log_event("test", "message")

    def test_log_event_respects_max_cap(self, tmp_db):
        """log_event must not keep more than MAX_EVENTS rows."""
        from database import log_event, get_engine, SystemEvent
        from sqlmodel import Session, select, func

        for i in range(MAX_EVENTS + 10):
            log_event("test", f"msg {i}")

        with Session(get_engine()) as s:
            count = s.exec(select(func.count()).select_from(SystemEvent)).one()

        assert count <= MAX_EVENTS, (
            f"Expected at most {MAX_EVENTS} rows, found {count}"
        )

    def test_log_event_keeps_newest(self, tmp_db):
        """After pruning, the newest events must be retained."""
        from database import log_event, get_engine, SystemEvent
        from sqlmodel import Session, select

        for i in range(MAX_EVENTS + 5):
            log_event("test", f"msg {i}")

        with Session(get_engine()) as s:
            events = s.exec(
                select(SystemEvent).order_by(SystemEvent.id.desc()).limit(5)
            ).all()

        messages = [e.message for e in events]
        for i in range(MAX_EVENTS, MAX_EVENTS + 5):
            assert f"msg {i}" in messages, (
                f"'msg {i}' was pruned but should have been kept"
            )

    def test_log_event_uses_count_not_full_scan(self, tmp_db):
        """Cleanup must use COUNT(*), not a full table scan."""
        import database as db_mod
        from sqlmodel import Session as _Session

        select_queries: list[str] = []
        original_exec = _Session.exec

        def tracking_exec(self, statement, *args, **kwargs):
            q = str(statement).upper()
            if q.lstrip().startswith("SELECT"):
                select_queries.append(str(statement))
            return original_exec(self, statement, *args, **kwargs)

        _Session.exec = tracking_exec
        try:
            for i in range(db_mod.MAX_EVENTS + 2):
                db_mod.log_event("test", f"m{i}")
        finally:
            _Session.exec = original_exec

        full_table_selects = [
            q for q in select_queries
            if "system_events" in q.lower()
            and "count" not in q.lower()
            and "limit" not in q.lower()
        ]
        assert not full_table_selects, (
            f"Full-table SELECT(s) found in log_event: {full_table_selects}"
        )