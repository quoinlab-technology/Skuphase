"""Simple HTML email templates for auth flows."""

from __future__ import annotations

from html import escape

_BASE_STYLE = (
    "font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;"
    "padding:24px;color:#1f2937;line-height:1.5;"
)
_BUTTON_STYLE = (
    "display:inline-block;background:#1d4ed8;color:#ffffff;padding:12px 22px;"
    "border-radius:6px;text-decoration:none;font-weight:bold;"
)


def _wrap(title: str, body_html: str) -> str:
    return f"""
    <html><body style="{_BASE_STYLE}">
        <h2 style="color:#1d4ed8;">SkuPhase</h2>
        <h3>{escape(title)}</h3>
        {body_html}
        <p style="color:#6b7280;font-size:12px;margin-top:32px;">
            If you did not request this, you can safely ignore this email.
        </p>
    </html></body>
    """


def _button(url: str, label: str) -> str:
    return f'<p><a href="{escape(url)}" style="{_BUTTON_STYLE}">{escape(label)}</a></p>'


def _fallback_link(url: str) -> str:
    return (
        f'<p style="color:#6b7280;font-size:13px;">'
        f'Or copy this link into your browser:<br>{escape(url)}</p>'
    )


def build_reset_password_email(reset_url: str) -> str:
    body = (
        "<p>We received a request to reset your SkuPhase password.</p>"
        + _button(reset_url, "Reset password")
        + _fallback_link(reset_url)
        + "<p>This link expires in 1 hour.</p>"
    )
    return _wrap("Reset your password", body)


def build_verify_email(verify_url: str) -> str:
    body = (
        "<p>Welcome to SkuPhase! Confirm your email address to activate your account.</p>"
        + _button(verify_url, "Verify email")
        + _fallback_link(verify_url)
    )
    return _wrap("Verify your email", body)


def build_invite_email(invitee_name: str, school_name: str, invite_url: str) -> str:
    body = (
        f"<p>Hello {escape(invitee_name)},</p>"
        f"<p>You have been invited to join <strong>{escape(school_name)}</strong> "
        "on SkuPhase. Accept the invitation to set your password and activate "
        "your staff account.</p>"
        + _button(invite_url, "Accept invitation")
        + _fallback_link(invite_url)
    )
    return _wrap("You're invited to SkuPhase", body)
