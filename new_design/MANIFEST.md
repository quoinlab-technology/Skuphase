# SkuPhase approved visual references: phases 1-4

These images are the visual contract for the FastHTML implementation in this
repository. They describe hierarchy, spacing, surfaces, typography and
responsive behaviour. Backend APIs, schemas and permissions remain the source
of truth for available actions and product copy.

## Phase 1: shared app shell

| Image | Route/state | Notes |
| --- | --- | --- |
| `P01_app_shell_dashboard_desktop.png` | `/app`, school administrator, desktop | Replace dead Documents, Assets and RAG links with Curriculum. |
| `P01_app_shell_dashboard_mobile.png` | `/app`, mobile | Desktop sidebar becomes an offcanvas menu; bottom nav remains visible. |
| `P01_mobile_navigation_open.png` | any `/app/*`, mobile menu open | Role-filter navigation only. |
| `P01_sidebar_collapsed_desktop.png` | desktop optional state | A future enhancement; the current visible sidebar remains the functional baseline. |

## Phase 2: public routes

| Image | Route |
| --- | --- |
| `P02_landing_default_desktop.png` | `/` |
| `P02_landing_default_mobile.png` | `/` at 390px |
| `P02_how_it_works_desktop.png` | `/how-it-works` |
| `P02_contact_desktop.png` | `/contact` |
| `P02_privacy_desktop.png` | `/privacy` |
| `P02_terms_desktop.png` | `/terms` |

All historical document upload, RAG retrieval and asset-catalogue copy shown
in the prototype is intentionally replaced by curriculum scope, question-bank,
review, preflight and export language.

## Phase 3: authentication

| Image | Route/state |
| --- | --- |
| `P03_login_default_desktop.png` | `/login` |
| `P03_login_default_mobile.png` | `/login` at 390px |
| `P03_register_school_step1_desktop.png` | `/register?mode=school` |
| `P03_register_school_step2_desktop.png` | school registration second step |

## Phase 4: dashboard and Curriculum Explorer

The dashboard shell reference is `P01_app_shell_dashboard_desktop.png`.
Curriculum Explorer has no direct prototype image because it replaces the
removed RAG/Documents/Assets modules. Its approved functional contract is:

- `/app/curriculum` starts with class, subject and term selectors plus weekly
  NERDC topics.
- Search results expose a clear route into the curriculum-first exam wizard.
- The page uses the same shell, white-card surface, responsive three/two/one
  column grid and feedback states as the phase 1 dashboard.
- Individual teachers see Curriculum Explorer rather than school-only
  governance controls.
