"""Feedback components (FRONTEND_SPEC.md §5): flash + toasts.

M2 uses server-rendered flashes for full-page form flows (register, login,
password reset). HTMX flows and authenticated AppShell pages use Faststrap's
ModernToast / ToastContainer so feedback appears smoothly without cluttering
page layouts or producing duplicate alert boxes.
"""

from __future__ import annotations

from starlette.requests import Request

from fasthtml.common import Div, Script
from faststrap import Alert, ModernToast, ToastContainer

_FLASH_KEY = "flash"

_VARIANT_TO_ALERT = {
    "success": "success",
    "danger": "danger",
    "warning": "warning",
    "info": "info",
}

_VARIANT_TO_INTENT = {
    "success": "success",
    "danger": "danger",
    "warning": "warning",
    "info": "info",
}

_VARIANT_TO_TITLE = {
    "success": "Success",
    "danger": "Error",
    "warning": "Notice",
    "info": "Info",
}


def set_flash(session, variant: str, message: str) -> None:
    """Queue a one-shot banner message for the next rendered page."""
    session[_FLASH_KEY] = {"variant": variant, "message": message}


def push_flash(request, message: str, variant: str = "info") -> None:
    """Convenience helper: queue a flash message from request or session."""
    sess = getattr(request, "session", request)
    set_flash(sess, variant=variant, message=message)


def pop_flash(request: Request):
    """Read-and-clear the queued flash; returns a Flash component or None."""
    data = request.session.pop(_FLASH_KEY, None)
    if not data:
        return None
    return Flash(data.get("message", ""), variant=data.get("variant", "info"))


def Flash(message: str, variant: str = "info"):
    """Inline Alert with a screen-reader-safe variant label (§8 a11y).

    Used in full-page redirect flows and auth pages (which have no ToastContainer)
    to display feedback clearly above forms.
    """
    label = _VARIANT_TO_TITLE.get(variant, variant.title())
    return Div(
        Alert(
            f"{label}: {message}",
            variant=_VARIANT_TO_ALERT.get(variant, "info"),
        ),
        cls="mb-3",
    )


def show_toast(message: str, variant: str = "info", title: str | None = None, **kwargs):
    """Return a ModernToast for HTMX partial responses or flash conversions.

    Usage::

        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Action failed."), "danger")
        return show_toast("Saved successfully!", "success")
    """
    resolved_title = title or _VARIANT_TO_TITLE.get(variant, "Notice")
    intent = _VARIANT_TO_INTENT.get(variant, "info")
    return ModernToast(
        title=resolved_title,
        message=message,
        intent=intent,
        duration=5000,
        dismissible=True,
        **kwargs,
    )


def to_toast(flash_or_msg, variant: str = "info"):
    """Convert a Flash component, string, or existing toast into a ModernToast."""
    if flash_or_msg is None:
        return None
    if isinstance(flash_or_msg, str):
        return show_toast(flash_or_msg, variant=variant)
    attrs = getattr(flash_or_msg, "attrs", {})
    if attrs.get("data-fs-modern-toast"):
        return flash_or_msg
    try:
        alert_child = flash_or_msg.children[0]
        text = str(alert_child.children[0])
        if ": " in text:
            label, message = text.split(": ", 1)
            var = "danger" if label == "Error" else ("success" if label == "Success" else ("warning" if label == "Notice" else "info"))
            return show_toast(message, variant=var, title=label)
        return show_toast(text, variant=variant)
    except Exception:
        return flash_or_msg


def app_toast_container(toast=None):
    """Persistent toast container to embed once in the AppShell.

    If an initial toast (e.g. from flash on redirect) is provided, it is mounted
    directly inside the container so it appears immediately on page load.
    Includes an active runtime script for auto-dismissal and close button handling.
    """
    toasts = [toast] if toast is not None else []
    dismiss_script = Script("""
    (function() {
      function dismissToastEl(el) {
        if (!el || el._isDismissing) return;
        el._isDismissing = true;
        el.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        el.style.opacity = '0';
        el.style.transform = 'translateY(10px) scale(0.96)';
        setTimeout(function() {
          if (el && el.parentNode) el.parentNode.removeChild(el);
        }, 320);
      }

      function bindToast(toastEl) {
        if (!toastEl || toastEl._toastBound) return;
        toastEl._toastBound = true;

        var duration = parseInt(toastEl.getAttribute('data-fs-duration') || '4500', 10);
        var timer = null;
        if (duration > 0) {
          timer = setTimeout(function() {
            dismissToastEl(toastEl);
          }, duration);
        }

        toastEl.addEventListener('mouseenter', function() {
          if (timer) { clearTimeout(timer); timer = null; }
        });
        toastEl.addEventListener('mouseleave', function() {
          if (!toastEl._isDismissing && duration > 0) {
            timer = setTimeout(function() {
              dismissToastEl(toastEl);
            }, 2500);
          }
        });

        var closeBtns = toastEl.querySelectorAll('.btn-close, [data-fs-dismiss="true"], [data-bs-dismiss="toast"]');
        closeBtns.forEach(function(btn) {
          btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (timer) clearTimeout(timer);
            dismissToastEl(toastEl);
          });
        });
      }

      function initAllToasts() {
        var toastSel = '.' + ['faststrap', 'modern', 'toast'].join('-');
        var toasts = document.querySelectorAll(toastSel + ', [data-fs-modern-toast], #app-toast-container .toast, #app-toast-container [role="status"], #app-toast-container [role="alert"]');
        toasts.forEach(bindToast);
      }

      if (document.readyState !== 'loading') {
        initAllToasts();
      } else {
        document.addEventListener('DOMContentLoaded', initAllToasts);
      }

      document.addEventListener('htmx:afterSwap', function() {
        setTimeout(initAllToasts, 20);
      });
      document.addEventListener('htmx:oobAfterSwap', function() {
        setTimeout(initAllToasts, 20);
      });
    })();
    """)
    return Div(
        ToastContainer(*toasts, position="bottom-end", container_id="app-toast-container"),
        dismiss_script,
    )
