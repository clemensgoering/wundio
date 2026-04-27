"""
Additional database tests – log_event cap behaviour.
Append these methods to the TestDatabase class in tests/phase0/test_core.py.
"""

# ── Patch: add to class TestDatabase in tests/phase0/test_core.py ────────────

    def test_log_event_respects_max_cap(self, tmp_db):
        """log_event must not keep more than MAX_EVENTS rows."""
        from database import log_event, get_engine, MAX_EVENTS, SystemEvent
        from sqlmodel import Session, select, func

        # Insert MAX_EVENTS + 10 events
        for i in range(MAX_EVENTS + 10):
            log_event("test", f"msg {i}")

        with Session(get_engine()) as s:
            count = s.exec(select(func.count()).select_from(SystemEvent)).one()

        assert count <= MAX_EVENTS, (
            f"Expected at most {MAX_EVENTS} rows, found {count}"
        )

    def test_log_event_keeps_newest(self, tmp_db):
        """After pruning, the newest events must be retained."""
        from database import log_event, get_engine, MAX_EVENTS, SystemEvent
        from sqlmodel import Session, select

        for i in range(MAX_EVENTS + 5):
            log_event("test", f"msg {i}")

        with Session(get_engine()) as s:
            events = s.exec(
                select(SystemEvent).order_by(SystemEvent.id.desc()).limit(5)
            ).all()

        messages = [e.message for e in events]
        # The most recent messages should survive
        for i in range(MAX_EVENTS, MAX_EVENTS + 5):
            assert f"msg {i}" in messages, f"'msg {i}' was pruned but should have been kept"

    def test_log_event_count_stays_o1(self, tmp_db, monkeypatch):
        """log_event must use COUNT(*), never load all rows into Python memory.

        We verify this indirectly: the cleanup path must not call .all() on a
        full-table select. We monkeypatch Session.exec to track query strings.
        """
        import database as db_mod
        from sqlmodel import select, func
        from database import SystemEvent

        all_calls = []
        original_exec = db_mod.Session.exec

        def tracking_exec(self, statement, *args, **kwargs):
            all_calls.append(str(statement))
            return original_exec(self, statement, *args, **kwargs)

        monkeypatch.setattr(db_mod.Session, "exec", tracking_exec)

        # Trigger the cleanup branch by going over the cap
        for i in range(db_mod.MAX_EVENTS + 2):
            db_mod.log_event("test", f"m{i}")

        # No query should select all columns from system_events without a LIMIT/COUNT
        full_table_selects = [
            q for q in all_calls
            if "system_events" in q.lower()
            and "count" not in q.lower()
            and "limit" not in q.lower()
        ]
        assert not full_table_selects, (
            f"Found full-table select(s) in log_event: {full_table_selects}"
        )