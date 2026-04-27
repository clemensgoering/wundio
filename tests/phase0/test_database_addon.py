"""
Database log_event cap tests.

Complements TestDatabase in tests/phase0/test_core.py.
Can be merged there or kept as a separate module.
"""
from database import MAX_EVENTS


class TestLogEventCap:
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

    def test_log_event_does_not_load_all_rows(self, tmp_db):
        """log_event cleanup must use COUNT(*), not a full table scan.

        Verified by checking that no query selects all system_events columns
        without a LIMIT or COUNT aggregate during the cleanup path.
        """
        import database as db_mod
        from sqlmodel import Session as _Session

        all_queries: list[str] = []
        original_exec = _Session.exec

        def tracking_exec(self, statement, *args, **kwargs):
            all_queries.append(str(statement))
            return original_exec(self, statement, *args, **kwargs)

        _Session.exec = tracking_exec
        try:
            for i in range(db_mod.MAX_EVENTS + 2):
                db_mod.log_event("test", f"m{i}")
        finally:
            _Session.exec = original_exec

        full_table_selects = [
            q for q in all_queries
            if "system_events" in q.lower()
            and "count" not in q.lower()
            and "limit" not in q.lower()
        ]
        assert not full_table_selects, (
            f"Full-table select(s) found in log_event: {full_table_selects}"
        )