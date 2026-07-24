from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.routers.internal.statements import latest_party_id


def membership(party_id, *, start_date=None, end_date=None, created_at=None):
    return SimpleNamespace(
        party_id=party_id,
        start_date=start_date,
        end_date=end_date,
        created_at=created_at or datetime(2026, 1, 1),
    )


def test_latest_party_id_prefers_current_membership_with_latest_start_date():
    old_party_id = uuid4()
    current_party_id = uuid4()
    newer_current_party_id = uuid4()
    politician = SimpleNamespace(
        memberships=[
            membership(old_party_id, start_date=date(2020, 1, 1), end_date=date(2024, 1, 1)),
            membership(current_party_id, start_date=date(2024, 1, 2)),
            membership(newer_current_party_id, start_date=date(2025, 1, 1)),
        ]
    )

    assert latest_party_id(politician) == newer_current_party_id


def test_latest_party_id_uses_latest_ended_membership_when_no_current_membership():
    older_party_id = uuid4()
    latest_party = uuid4()
    politician = SimpleNamespace(
        memberships=[
            membership(older_party_id, start_date=date(2020, 1, 1), end_date=date(2022, 1, 1)),
            membership(latest_party, start_date=date(2022, 1, 2), end_date=date(2024, 1, 1)),
        ]
    )

    assert latest_party_id(politician) == latest_party
