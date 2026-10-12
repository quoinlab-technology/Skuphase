from app.utils.email import normalize_email


def test_normalize_email_is_trimmed_and_casefolded():
    assert normalize_email("  Service.QuoinLab@GMAIL.COM ") == "service.quoinlab@gmail.com"
