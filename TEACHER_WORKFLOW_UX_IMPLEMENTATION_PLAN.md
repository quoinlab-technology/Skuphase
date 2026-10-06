# SkuPhase Teacher Workflow UX Implementation Plan

**Status:** Proposed implementation direction  
**Date:** 2026-10-06  
**Scope:** Package A assessment workflows, Package B teaching workflows, and curriculum authoring  
**Primary audience:** Nigerian teachers and school administrators, including users working primarily from low-cost Android phones and unreliable or low-bandwidth connections

## 1. Why this document exists

SkuPhase has accumulated substantial capability: curriculum-aligned AI exam generation, a sophisticated manual question editor, equations and diagrams, PDF exports, lesson plans, AI lesson notes, weekly exercises, coverage tracking, and school-scoped curriculum authoring.

The risk is no longer primarily missing capability. The risk is that ordinary teachers may not discover or successfully use the capability because too many decisions are exposed at once.

This document records how that conclusion was reached and defines the implementation direction. It is intended to prevent the project from repeatedly adding features without reducing user friction.

## 2. The underlying problem

SkuPhase is designed for schools in rural and lower-connectivity areas in Nigeria. The users are not necessarily inexperienced teachers; many are experienced educators who may have limited confidence with complex software, limited time, small screens, intermittent connectivity, and little tolerance for losing work.

The current product can be technically powerful while still failing operationally if a teacher:

- does not know where to start;
- cannot tell which class, subject, term, or week is active;
- cannot distinguish official curriculum text from school corrections;
- is overwhelmed by manual exam controls;
- cannot trust the generated PDF;
- cannot understand an error or permission message;
- cannot complete a workflow comfortably on a phone; or
- must understand the data model before receiving a useful result.

The goal is therefore not to remove SkuPhase's advanced capabilities. The goal is to make the first useful outcome simple while keeping advanced control available when needed.

## 3. Current implementation: what the system can do

### 3.1 Package A assessment capabilities

The assessment engine currently supports:

- manual exam creation;
- AI exam generation grounded in curriculum topics;
- question creation, editing, duplication, deletion, and reordering;
- structured and multipart question blocks;
- question marks and marking information;
- equations and formula insertion;
- diagram insertion and preview;
- question-bank reuse;
- AI-assisted suggestions with teacher approval flow;
- exam review and preflight checks;
- student papers;
- answer keys;
- marking guides;
- worksheets;
- OMR-related outputs;
- PDF generation and downloads;
- school-specific settings used in generated documents.

### 3.2 Package B teaching capabilities

The Teaching workspace currently supports:

- class, subject, and term selection;
- scheme-week selection from canonical curriculum data;
- lesson-plan creation;
- activities and assessment notes;
- instructional materials/resources;
- AI lesson-note drafting;
- teacher lesson-note editing and submission;
- school-admin approval;
- syllabus coverage progression;
- coverage summary metrics;
- incomplete-coverage warnings;
- weekly exercise creation;
- worksheet PDF export/download.

### 3.3 Curriculum capabilities

The curriculum system currently supports:

- primary and secondary curriculum datasets;
- class and subject exploration;
- term/week browsing;
- curriculum search;
- school-scoped scheme-of-work overrides;
- administrator correction of canonical topic/subtopic text;
- teacher-local notes and resources;
- school-specific archive/revert behavior;
- curriculum records shared by teaching and generation workflows.

### 3.4 Current shell and responsive behavior

The application currently has:

- a desktop sidebar;
- sidebar collapse behavior;
- authenticated top navigation;
- mobile bottom navigation;
- FastHTML/Faststrap cards, forms, selects, modals, and buttons;
- responsive teaching, curriculum, exam, and review pages.

## 4. Current implementation: what remains difficult or incomplete

The system is capable, but the default workflow is not yet sufficiently guided.

### 4.1 Package A friction

- Manual exam creation exposes many decisions at once.
- A phone user must edit a long sequence of questions in a dense form.
- Generic question entry does not naturally guide a teacher toward the correct question type.
- Equations, diagrams, marks, answers, and subparts can make a question card intimidating.
- AI output still requires careful review, but that review can feel like a second complex editor.
- PDF trust depends on checking layout, spacing, diagrams, formulas, school identity, marks, and page breaks.
- Generated outputs need a clearer final summary before export.

### 4.2 Package B friction

- The user must know to go to Teaching before receiving a clear task recommendation.
- Scope selection does not always explain its effect.
- Imported curriculum text can be difficult to read when words are joined or raw formatting is poor.
- Activities, assessment notes, and resources need examples.
- A long AI lesson note is harder to edit than a set of clearly separated sections.
- Coverage terminology is more administrative than teacher-oriented.
- Weekly exercise creation is currently simple and mostly line-based.
- Teachers may not know whether work is saved, submitted, approved, or only drafted.

### 4.3 Curriculum authoring friction

- Official text and school corrections must be visually distinct.
- Archive and revert are powerful operations and need clear consequences.
- Teachers need local notes/resources without being exposed to unnecessary canonical-editing complexity.
- A corrected curriculum record must visibly remain connected to the teaching and exam workflows.

### 4.4 Responsive and low-connectivity friction

- Dense desktop controls cannot simply be squeezed onto a phone.
- Fixed mobile navigation must never hide the next input or action.
- Ultra-narrow devices around 280px still need to avoid horizontal overflow.
- External CDN assets can fail in constrained environments; the project should track this as a deployment concern even when the current UI depends on CDN delivery.
- A slow response should have a clear loading state rather than appearing to do nothing.

## 5. Why the teacher probe was conducted

The probe intentionally assumed the perspective of an older Nigerian woman teacher who is experienced in teaching but not necessarily comfortable with complex software.

The purpose was constructive:

- identify actions that would be obviously difficult;
- distinguish actions that are only slightly difficult;
- identify actions that are already easy;
- determine whether the product should be simplified or guided;
- challenge the workflow before adding more features;
- avoid over-engineering around technically impressive but rarely used controls;
- identify the moments most likely to prevent school adoption.

The probe was not a criticism of the system's ambition. It was a test of whether the ambition is accessible to the intended user.

## 6. What the probe exposed

### 6.1 Obviously difficult actions

The following actions are likely to be difficult for an ordinary teacher, especially on a phone:

1. Building a complete manual exam from a blank starting point.
2. Editing many questions, equations, diagrams, marks, answers, and subparts in one continuous form.
3. Understanding imported curriculum corrections and their effect on downstream generation.
4. Understanding the difference between planned, in-progress, completed, and verified coverage.
5. Trusting a generated PDF without a strong final preview and summary.
6. Reviewing AI output when many questions are questionable or need correction.

### 6.2 Slightly difficult actions

These actions are understandable but need guidance:

1. Selecting class, subject, term, and scheme week.
2. Completing activities, assessment notes, and resources.
3. Editing a long AI lesson note.
4. Creating exercises with different question formats.
5. Finding previous exams and worksheets over time.
6. Understanding permission failures.

### 6.3 Probably easy actions

These are good foundations to preserve:

1. Logging in and opening the authenticated workspace.
2. Browsing curriculum by class, subject, term, and week.
3. Starting an AI exam workflow.
4. Drafting an AI lesson note.
5. Marking a topic as taught when the action is plainly named.
6. Exporting an already-created worksheet or exam.
7. Using a simple mobile bottom navigation.

## 7. Decision: guided complexity, not reduced capability

The probe supports a progressive-disclosure strategy.

SkuPhase should not remove equations, diagrams, blueprints, question blocks, curriculum overlays, or document exports. Those capabilities are part of its value proposition.

Instead:

- the first screen should offer one clear task;
- defaults should cover normal school use;
- advanced options should be hidden until requested;
- each workflow should show the current context;
- generated output should be reviewed in simple sections;
- teachers should receive useful output before encountering advanced controls;
- administrators and expert users should retain full control through Advanced mode.

The product should feel like:

> Tell me what you are preparing, and guide me to a finished, printable result.

It should not feel like:

> Here are all the controls; determine the correct sequence yourself.

## 7.1 Explicit preservation decision: Advanced mode remains intact

The existing workflows are not being discarded, rewritten, or demoted. They
represent the product's professional capability and should remain available as
the **Pro/Advanced mode**.

The implementation direction is an additional access layer, not a replacement
architecture:

- Existing manual exam creation remains available for expert users.
- Existing advanced question blocks, equations, diagrams, marking controls,
  blueprints, exports, and review tools remain available.
- Existing administrator and curriculum-authoring controls remain available.
- Existing routes and persistence contracts should be preserved wherever
  possible.
- The Guided/Novice flow should call the same underlying services and editors,
  using sensible defaults and progressive disclosure.
- A user should be able to move from Guided mode into Advanced mode without
  losing work or starting over.
- Advanced mode should be labelled clearly rather than hidden permanently.

The desired relationship is:

```text
Guided/Novice entry
        |
        v
Shared curriculum, lesson, question, generation, and export services
        |
        +--> Pro/Advanced editor and controls
```

This prevents two dangerous outcomes:

1. Rebuilding a second simplified system that later diverges from the proven
   advanced workflow.
2. Removing capabilities that expert teachers and administrators genuinely
   need.

The novice experience is therefore a simpler front door, not a simpler engine.

## 8. Main implementation plan

### Phase 1 — Reduce orientation friction

**Objective:** Make the first useful action obvious without changing the core data model.

Implement:

- task-oriented dashboard actions:
  - Prepare a lesson;
  - Create classwork;
  - Generate an exam;
  - Continue unfinished work;
  - Review submitted work;
- clear active-context summary on Teaching, Curriculum, and Exams pages;
- consistent display of class, subject, term, and week;
- clearer empty states with a recommended next action;
- plain-language permission and validation messages;
- save/draft/submitted/approved state labels;
- examples in activity, assessment, resources, and instruction fields;
- visible loading states for AI generation, curriculum loading, and exports.
- Guided/Advanced entry choices that route users into the appropriate existing
  workflow without duplicating the underlying feature.

**Acceptance criteria:**

- A first-time teacher can identify the next action within ten seconds.
- Every generated result visibly states the class, subject, term, and selected topics.
- No routine error message uses only technical language.

### Phase 2 — Build the guided teacher journey

**Objective:** Give Teaching and Exam workflows a common, predictable sequence.

The shared flow should be:

1. Context — class, subject, term, and school.
2. Curriculum — one or more weeks/topics.
3. Output — lesson note, exercise, worksheet, or examination.
4. Generate/build — simple defaults first.
5. Review — edit, approve, regenerate, remove, or save draft.
6. Export/continue — produce the required document or return to the workspace.

Implement:

- step indicator or clear progress language;
- Back and Continue controls;
- safe preservation of entered data when changing scope;
- final summary before export;
- consistent review and save behavior across outputs.

**Acceptance criteria:**

- A teacher can complete a normal lesson-to-exercise workflow without understanding database or API terminology.
- Changing a selection does not silently discard work.
- The user always knows whether work is a draft, submitted, approved, or exported.

### Phase 3 — Improve AI lesson-note usability

**Objective:** Make AI assistance useful without requiring prompt-writing skill.

Implement guided actions:

- Add Nigerian/local examples.
- Make shorter.
- Simplify for slower learners.
- Add practical activity.
- Add assessment questions.
- Improve wording.
- Regenerate.

Render notes as editable sections:

- objectives;
- starter activity;
- explanation;
- guided practice;
- assessment;
- differentiation;
- instructional materials.

**Acceptance criteria:**

- A teacher can improve a draft using buttons or short fields rather than writing a long AI prompt.
- Each section can be edited without navigating a giant text block.
- The system clearly labels AI text as a draft until teacher/admin approval.

### Phase 4 — Improve weekly exercise authoring

**Objective:** Move beyond one-question-per-line worksheets while keeping simple creation available.

Implement a question-type chooser:

- multiple choice;
- short answer;
- theory/essay;
- fill in the blank;
- matching;
- calculation;
- diagram-based;
- multipart.

Keep the quick path:

> Add simple question

Add advanced controls inside each question block:

- marks;
- answer;
- options;
- hints;
- equation/diagram insertion;
- difficulty;
- learner instructions.

**Acceptance criteria:**

- A teacher can create a useful basic exercise in under two minutes.
- Advanced question types do not make the basic path more complicated.
- Exported worksheets preserve question structure and answer spacing.

### Phase 5 — Improve AI exam generation and review

**Objective:** Make AI generation easy to start and trustworthy to approve.

The default wizard should ask only for:

- class;
- subject;
- curriculum topics;
- number of questions;
- duration.

Advanced options should be collapsible:

- question-type distribution;
- difficulty;
- Bloom levels;
- marks and blueprint constraints;
- formula and diagram requirements;
- local-context instructions.

The review screen should support question-level actions:

- approve;
- edit;
- regenerate;
- remove;
- flag.

Show review indicators for:

- curriculum alignment;
- answer correctness;
- mark allocation;
- difficulty;
- duplicates;
- Nigerian relevance;
- diagram/formula rendering.

**Acceptance criteria:**

- A normal teacher can generate an exam without opening Advanced settings.
- A teacher can correct one bad question without restarting generation.
- The final export summary clearly identifies every document being produced.

### Phase 6 — Clarify curriculum authoring

**Objective:** Make school corrections powerful but safe and understandable.

Implement or refine:

- visual separation between official seeded text and school correction;
- explicit labels:
  - Official curriculum text;
  - School correction;
  - Local teacher notes;
- clear archive/revert consequences;
- confirmation before canonical changes or archive actions;
- teacher-local notes/resources without exposing canonical controls;
- indication of where the corrected text is used:
  - lesson plans;
  - teaching coverage;
  - exam generation.

**Acceptance criteria:**

- A teacher can add local notes without accidentally editing official text.
- An administrator understands exactly what archive and revert will affect.
- The same corrected curriculum is used consistently by Teaching and exam generation.

### Phase 7 — Mobile and low-bandwidth hardening

**Objective:** Make the guided workflows reliable on common Nigerian phones and connections.

Test at minimum:

- 280px;
- 320px;
- 360px;
- 390px;
- 430px;
- 768px;
- 1024px;
- 1280px;
- 1440px.

Verify:

- no horizontal scrolling;
- fixed navigation does not cover inputs or actions;
- equations and diagrams stay within safe preview containers;
- forms remain readable and tappable;
- loading and retry states are visible;
- page state survives slow responses and refreshes;
- essential pages remain usable when external assets are slow or unavailable.

**Acceptance criteria:**

- A teacher can complete the core guided workflow at 320px without horizontal scrolling.
- The 280px layout remains usable, even if compact.
- The last action on every long page can be reached above the fixed bottom navigation.

## 9. Operating modes

### Guided mode

Default for most teachers:

- short forms;
- sensible defaults;
- examples;
- one primary action;
- progressive disclosure;
- clear confirmation summaries;
- simple AI refinement actions.

### Advanced mode

Available for experienced teachers and administrators:

- complete exam blueprints;
- detailed marks and rubrics;
- formula and diagram controls;
- bulk question operations;
- imports/exports;
- canonical curriculum authoring;
- school policy and approval controls.

The modes must share the same data and not create parallel workflows.

## 10. What should not be implemented yet

To avoid over-engineering, do not begin with:

- a new frontend framework;
- a separate curriculum data model;
- a complex teacher training portal;
- a full offline-first rewrite;
- additional AI controls without a demonstrated teacher task;
- commercial pricing or partner API work;
- SMS student/fee modules;
- replacing working Faststrap components merely for visual novelty.

## 11. Measurement and validation plan

Every implementation phase should be tested with:

### Workflow measures

- time to first useful output;
- number of screens visited;
- number of required decisions;
- number of validation errors;
- number of times a user returns/backtracks;
- successful export rate;
- percentage of generated questions accepted without editing.

### Visual measures

- desktop and mobile screenshots;
- no horizontal overflow;
- no clipped controls;
- no fixed-nav overlap;
- readable equations and diagrams;
- clear hierarchy and spacing;
- visible focus states;
- meaningful empty/loading/error states.

### Trust measures

- correct class/subject/term in every output;
- correct marks and question count;
- correct answer key and marking guide;
- correct school identity;
- correct curriculum source;
- clear draft/submission/approval state.

## 12. Definition of done for this UX initiative

This initiative is complete when:

- a first-time teacher can prepare a lesson and exercise without external training;
- a teacher can generate and review an exam without touching advanced settings;
- a teacher can create a basic manual question quickly;
- advanced question authoring remains available when needed;
- curriculum corrections are clearly separated from official text;
- mobile workflows work at 320px without horizontal scrolling;
- generated PDFs are previewed and trusted before export;
- every workflow has clear draft, review, approval, and export states;
- browser verification and automated tests cover the changed surfaces;
- no new feature is accepted without a clear teacher task it solves.

## 13. Decision summary

The probe did not show that SkuPhase is too advanced. It showed that the advanced capabilities are presented too close to the surface for a first-time teacher.

The agreed direction is:

1. Keep the powerful assessment and curriculum engine.
2. Make the default path guided and task-oriented.
3. Use progressive disclosure for expert controls.
4. Use teacher language instead of internal workflow language.
5. Treat mobile and printed output as first-class product surfaces.
6. Validate every change with a realistic teacher workflow, not only a passing API test.

This gives SkuPhase a better chance of being adopted by real schools without sacrificing the capabilities that distinguish it from a basic exam form.
