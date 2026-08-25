"""ExamArchitect - AI Exam Generator for Nigerian Schools

A complete, fully clickable prototype built with FastHTML and Faststrap.
Refactored into modular structure for easy maintenance.
"""

from fasthtml.common import *
from faststrap import add_bootstrap, create_theme

import time
import os
from pages.landing_page import landing_page

# Read CSS files
# css_content = open("static/style.css").read()

# Define custom headers
hdrs = (
    # Style(css_content),
    # Cache control for development
    Meta(**{"http-equiv": "Cache-Control", "content": "no-cache, no-store, must-revalidate"}),
    Meta(**{"http-equiv": "Pragma", "content": "no-cache"}),
    Meta(**{"http-equiv": "Expires", "content": "0"}),
)

# Initialize FastHTML app
app = FastHTML(
    hdrs=hdrs,
)

# Create Nigerian-themed color scheme
nigerian_theme = create_theme(
    primary="#006A4E",      # Nigerian green
    secondary="#FFD700",    # Gold accent
    success="#28A745",
    info="#17A2B8",
    warning="#FFC107",
    danger="#DC3545"
)

# Add Bootstrap with Nigerian theme (mounts at /static/)
add_bootstrap(app, theme=nigerian_theme, mode="light")

# Manually mount assets directory at /assets/ to avoid conflict with Faststrap's /static/
from starlette.staticfiles import StaticFiles
from starlette.routing import Mount
import os

# Use absolute path to ensure correct directory resolution
assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
app.routes.insert(0, Mount("/assets", StaticFiles(directory=assets_path), name="assets"))

# Routes
@app.get("/")
def get_landing():
    return landing_page()

# @app.get("/dashboard")
# def get_dashboard():
#     return dashboard()

# @app.get("/exams")
# def get_exams():
#     return my_exams()

# @app.get("/exams/generate")
# def get_generate():
#     return generate_exam_wizard()

# @app.get("/exams/generate/step2")
# def get_generate_step2():
#     return generate_exam_step2()

# @app.get("/exams/generate/step3")
# def get_generate_step3():
#     return generate_exam_step3()

# @app.get("/drafts")
# def get_drafts():
#     return drafts_page()

# @app.get("/upload")
# def get_upload():
#     return upload_notes()

# @app.get("/settings")
# def get_settings():
#     return settings_page()



# -------------------------------------
# Lucide Icon Demo Route
# -------------------------------------
@app.route("/icons")
def show_icons():
    return Main(
        H2("Remix Icon Example"),
        Div(
            I(_class="ri-home-2-line text-3xl", style="font-size:48px;color:#0078ff;"),
            I(_class="ri-user-3-fill", style="font-size:48px;margin-left:1rem;color:#e63946;"),
            I(_class="ri-settings-3-line", style="font-size:48px;margin-left:1rem;color:#444;"),
            style="padding:2rem;display:flex;justify-content:center;align-items:center;"
        )
    )

# Initialize database (run once)
@app.on_event("startup")
def startup_event():
    print("Starting ExamArchitect application...")

if __name__ == "__main__":
    serve(port=5017)
