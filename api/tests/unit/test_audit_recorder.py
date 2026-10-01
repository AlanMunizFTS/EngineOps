import json
from datetime import date
from enum import StrEnum
from unittest.mock import Mock
from uuid import uuid4

import pytest

from ops_platform.adapters.db.sqlalchemy_audit_recorder import SqlAlchemyAuditRecorder


class ExampleStatus(StrEnum):
    OPEN = "open"


@pytest.mark.asyncio
async def test_record_normalizes_diff_values_for_jsonb() -> None:
    session = Mock()
    recorder = SqlAlchemyAuditRecorder(session)
    project_id = uuid4()
    actor_id = uuid4()
    entity_id = uuid4()

    await recorder.record(
        project_id=project_id,
        actor_id=actor_id,
        entity_type="task",
        entity_id=entity_id,
        action="task.updated",
        diff={
            "due_date": date(2026, 10, 15),
            "assignee_id": actor_id,
            "status": ExampleStatus.OPEN,
        },
    )

    audit_row = session.add.call_args.args[0]
    assert audit_row.diff_json == {
        "due_date": "2026-10-15",
        "assignee_id": str(actor_id),
        "status": "open",
    }
    json.dumps(audit_row.diff_json)
