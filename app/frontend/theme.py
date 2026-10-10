"""Brand theme tokens for the SkuPhase frontend (FRONTEND_SPEC.md §3.1).

Light mode only, per product decision. These values are the single source of
truth for both the CSS file (app/assets/css/custom.css) and any Python-side
styling decisions.
"""

BRAND = {
    "primary": "#00412E",      # deep green — shell, primary buttons
    "secondary": "#96BF8A",    # sage — accents, active nav (large text only)
    "secondary_dark": "#5f7d55",  # darkened sage — small text on light bg
    "shell": "#E8EAE5",        # page background
    "surface": "#FFFFFF",
    "accent": "#10b981",       # success / approved
    "warning": "#f59e0b",      # under review / pending
    "danger": "#ef4444",
}

FONT_FAMILY = "Nunito Sans"

CUSTOM_CSS = """
:root {
  --brand-primary: #00412E;
  --brand-secondary: #96BF8A;
  --brand-secondary-dark: #5f7d55;
  --brand-shell: #E8EAE5;
  --brand-surface: #FFFFFF;
  --brand-accent: #10b981;
  --brand-warning: #f59e0b;
  --brand-danger: #ef4444;

  --radius-sm: 0.5rem;
  --radius-md: 0.75rem;
  --space-sm: 0.75rem;
  --space-md: 1.5rem;
  --space-lg: 2.25rem;
}

body {
  background: var(--brand-shell);
  color: rgba(15, 23, 42, 0.94);
}

.app-navbar {
  background: var(--brand-primary);
}

.app-navbar .navbar-brand {
  color: #ffffff;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.app-navbar .nav-link {
  color: rgba(255, 255, 255, 0.85);
}

.app-hero-title {
  font-size: clamp(1.9rem, 4vw, 2.6rem);
  font-weight: 800;
  line-height: 1.05;
  letter-spacing: -0.03em;
  color: var(--brand-primary);
}

.app-section-title {
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: -0.015em;
}

.app-body-copy {
  font-size: 0.95rem;
  line-height: 1.65;
  color: rgba(15, 23, 42, 0.68);
}

.app-card {
  background: var(--brand-surface);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: var(--radius-md);
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.08);
}

.app-footer {
  background: var(--brand-primary);
  color: rgba(255, 255, 255, 0.85);
}

.btn-brand {
  background: var(--brand-primary);
  border-color: var(--brand-primary);
  color: #ffffff;
}

.btn-brand:hover {
  background: #003425;
  border-color: #003425;
  color: #ffffff;
}

.btn-outline-brand {
  background: transparent;
  border-color: var(--brand-primary);
  color: var(--brand-primary);
}

.btn-outline-brand:hover,
.btn-outline-brand:focus-visible {
  background: var(--brand-primary);
  border-color: var(--brand-primary);
  color: #ffffff;
}

.curriculum-week-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  flex: 0 0 auto;
}

.curriculum-week-meta .badge { margin: 0 !important; }
"""
