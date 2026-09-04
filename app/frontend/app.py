"""FastHTML frontend application instance (FRONTEND_SPEC sec 2.1).

One FastHTML app mounted inside the FastAPI application at "/". Bootstrap is
added exactly once, at import time. Session support is enabled via
``secret_key`` (Starlette SessionMiddleware) — the signed cookie carries auth
tokens from M2 onwards.
"""

from pathlib import Path

from fasthtml.common import FastHTML, Link
from faststrap import add_bootstrap, mount_assets

from app.config.settings import get_settings
from app.frontend.routes import auth as auth_routes
from app.frontend.routes import bank as bank_routes
from app.frontend.routes import curriculum as curriculum_routes
from app.frontend.routes import dashboard as dashboard_routes
from app.frontend.routes import exams as exams_routes
from app.frontend.routes import ops as ops_routes
from app.frontend.routes import proposals as proposals_routes
from app.frontend.routes import public as public_routes
from app.frontend.routes import settings as settings_routes
from app.frontend.routes import staff as staff_routes
from app.frontend.theme import FONT_FAMILY
from app.frontend.middleware import register_middlewares

settings = get_settings()

frontend_app = FastHTML(
    secret_key=settings.jwt_secret_key,
    sess_https_only=settings.app_env != "development",
    sess_path="/",
    exception_handlers={404: public_routes.not_found_handler, 500: public_routes.server_error_handler},
)

# Faststrap: exactly once, at startup (FRONTEND_SPEC sec 2.1).
add_bootstrap(
    frontend_app,
    mode="light",
    font_family=FONT_FAMILY,
)

# Brand CSS mounted after Faststrap so local tokens override cleanly (sec 3).
# Preload avoids flash of unstyled content.
frontend_app.hdrs.append(Link(rel="preload", href="/assets/css/custom.css", as_="style"))
frontend_app.hdrs.append(Link(rel="stylesheet", href="/assets/css/custom.css"))

# App-owned static assets (css/img) served from /assets (never /static).
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
mount_assets(frontend_app, str(_ASSETS_DIR))

# Security + CSRF middlewares (F46, F49, F50)
register_middlewares(frontend_app)

# Routes
public_routes.register_routes(frontend_app)
auth_routes.register_session_routes(frontend_app)
auth_routes.register_routes(frontend_app)
auth_routes.register_more_routes(frontend_app)
auth_routes.register_settlement_routes(frontend_app)
dashboard_routes.register_routes(frontend_app)
exams_routes.register_routes(frontend_app)
curriculum_routes.curriculum_routes(frontend_app)
bank_routes.register_routes(frontend_app)
proposals_routes.register_routes(frontend_app)
staff_routes.register_routes(frontend_app)
settings_routes.register_routes(frontend_app)
ops_routes.register_routes(frontend_app)
