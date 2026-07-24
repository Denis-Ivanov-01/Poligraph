from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.routers.internal.statements import current_party_id
from app.routers.internal.utils import templates


def test_current_party_id_uses_latest_open_membership():
    old_party_id = uuid4()
    current_party_id_value = uuid4()
    politician = SimpleNamespace(
        memberships=[
            SimpleNamespace(party_id=old_party_id, start_date=date(2020, 1, 1), end_date=date(2024, 1, 1)),
            SimpleNamespace(party_id=current_party_id_value, start_date=date(2024, 1, 2), end_date=None),
        ]
    )

    assert current_party_id(politician) == current_party_id_value


def test_new_statement_template_selects_default_party():
    party_id = uuid4()
    other_party_id = uuid4()
    html = templates.env.get_template("internal/statement_form.html").render(
        form_title="New statement",
        form_note="Draft details",
        form_action="/internal/statements",
        submit_label="Next",
        csrf_token="token",
        session={"role": "root_admin"},
        diagnostics_panel_enabled=False,
        diagnostics_panel_path="/internal/diagnostics",
        statement=None,
        selected_party_id=str(party_id),
        selected_politician_id="politician-1",
        politicians=[
            {"id": "politician-1", "full_name": "Politician 1", "current_party_id": str(party_id)},
            {"id": "politician-2", "full_name": "Politician 2", "current_party_id": str(other_party_id)},
        ],
        parties=[
            SimpleNamespace(id=party_id, full_name="Party"),
            SimpleNamespace(id=other_party_id, full_name="Other party"),
        ],
    )

    assert f'value="{party_id}" selected' in html
    assert f'data-current-party-id="{other_party_id}"' in html
    assert "data-party-sync-source" in html
    assert "data-party-sync-target" in html
