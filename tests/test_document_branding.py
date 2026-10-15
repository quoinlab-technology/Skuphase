from types import SimpleNamespace

from app.services.document_branding import resolve_document_branding


def _inputs(*, account_type, enabled=False, name=None, logo=None):
    return {
        "school": SimpleNamespace(name="Personal Workspace" if account_type == "individual_teacher" else "Greenfield Academy"),
        "settings": SimpleNamespace(
            document_display_name=name,
            personal_document_branding_enabled=enabled,
            logo_url=logo,
        ),
        "user": SimpleNamespace(account_type=account_type, full_name="Emeka Okafor"),
    }


def test_personal_workspace_defaults_to_registered_name_and_ignores_saved_custom_branding():
    result = resolve_document_branding(**_inputs(
        account_type="individual_teacher",
        enabled=False,
        name="Emeka Learning Centre",
        logo="https://assets.example/logo.png",
    ))

    assert result.display_name == "Emeka Okafor"
    assert result.logo_url is None


def test_personal_workspace_uses_opted_in_custom_identity_and_logo():
    result = resolve_document_branding(**_inputs(
        account_type="individual_teacher",
        enabled=True,
        name="Emeka Learning Centre",
        logo="https://assets.example/logo.png",
    ))

    assert result.display_name == "Emeka Learning Centre"
    assert result.logo_url == "https://assets.example/logo.png"


def test_opted_in_personal_branding_falls_back_to_registered_name_when_blank():
    result = resolve_document_branding(**_inputs(account_type="individual_teacher", enabled=True))

    assert result.display_name == "Emeka Okafor"
    assert result.logo_url is None


def test_school_uses_admin_document_name_or_school_name_and_shared_logo():
    custom = resolve_document_branding(**_inputs(
        account_type="school_staff",
        name="Greenfield International School",
        logo="https://assets.example/school.png",
    ))
    fallback = resolve_document_branding(**_inputs(account_type="school_staff", logo="https://assets.example/school.png"))

    assert custom.display_name == "Greenfield International School"
    assert custom.logo_url == "https://assets.example/school.png"
    assert fallback.display_name == "Greenfield Academy"
    assert fallback.logo_url == "https://assets.example/school.png"
