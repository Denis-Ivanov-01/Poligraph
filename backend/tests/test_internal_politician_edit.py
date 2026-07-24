from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.routers.internal.politicians import current_membership, set_current_party


class FakeDb:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)


def membership(party_id, *, start_date=None, end_date=None):
    return SimpleNamespace(
        party_id=party_id,
        start_date=start_date,
        end_date=end_date,
    )


def test_current_membership_prefers_latest_open_membership():
    older_party_id = uuid4()
    current_party_id = uuid4()
    politician = SimpleNamespace(
        memberships=[
            membership(older_party_id, start_date=date(2020, 1, 1)),
            membership(current_party_id, start_date=date(2024, 1, 1)),
        ]
    )

    assert current_membership(politician).party_id == current_party_id


def test_set_current_party_closes_old_open_membership_and_adds_new_one():
    old_party_id = uuid4()
    new_party_id = uuid4()
    old_membership = membership(old_party_id, start_date=date(2020, 1, 1))
    politician = SimpleNamespace(id=uuid4(), memberships=[old_membership])
    db = FakeDb()

    set_current_party(db, politician, str(new_party_id))

    assert old_membership.end_date == date.today()
    assert len(db.added) == 1
    assert str(db.added[0].party_id) == str(new_party_id)


def test_set_current_party_keeps_matching_current_membership():
    party_id = uuid4()
    existing = membership(party_id, start_date=date(2020, 1, 1))
    politician = SimpleNamespace(id=uuid4(), memberships=[existing])
    db = FakeDb()

    set_current_party(db, politician, str(party_id))

    assert existing.end_date is None
    assert db.added == []
