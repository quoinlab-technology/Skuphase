"""Canonical email handling for account identity lookups."""


def normalize_email(value: str) -> str:
    """Trim and case-fold an email address for storage and comparisons.

    Email local-parts are technically case-sensitive in the RFC, but treating
    account email as case-insensitive is the predictable behaviour users expect
    and prevents duplicate identities across registration, invitations, and
    login.
    """
    return str(value or "").strip().casefold()
