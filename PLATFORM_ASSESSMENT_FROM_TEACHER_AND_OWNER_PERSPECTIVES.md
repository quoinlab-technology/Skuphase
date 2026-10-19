# SkuPhase: an honest platform assessment from the classroom and school office

**Prepared:** 16 October 2026  
**Audience:** SkuPhase product team, pilot schools, and prospective school partners  
**Scope:** Ease of use for an older, non-technical Nigerian teacher; willingness of a principal or school owner to pilot the platform; and practical recommendations for building trust and day-to-day value.

## Executive view

SkuPhase addresses real, recurring school work: planning lessons from a scheme of work and preparing classroom exercises and examination papers. Its curriculum grounding, printable outputs, teacher workflows, and school review roles give it a more specific purpose than a general school administration package. The project is substantial, and the available browser audit demonstrated complete teaching journeys: creating a plan, generating and editing an AI note, saving and submitting it, approval, coverage tracking, and worksheet creation and PDF download.

My honest assessment is that the platform has a credible foundation and a meaningful niche, but the evidence does **not** yet justify presenting it as a dependable replacement for established school routines across all schools. In the dated Pass 2 browser audit, several correctness and communication defects appeared in the outputs teachers depend on. Some are fixed in the current source: lesson-note export links, lesson-note export handlers, worksheet question marks and types, answer-key fields, and the Teaching page's flash-message handling are now present. Those source checks are encouraging, but they do not establish that the current deployed version has been re-tested or that every related PDF is now correct. Intermittent teaching-page failures under load and other export findings also need a fresh end-to-end check.

For the older teacher in the question, the system is **learnable with a short, patient introduction and a nearby support person**, but I would not assume she can confidently use every current capability alone on her phone on the first day. I would invite a school owner to a **small, supported pilot** focused on lesson plans, notes, and printable papers after the output and reliability checks below pass. I would not yet advise the owner to abandon the old method or make the platform mandatory school-wide.

This is a reasoned persona assessment based on the code, the supplied project documents, and the recorded browser audit. It is **not** a live usability interview with a 60-year-old teacher or a field study in a Nigerian school. Actual teacher observation could change these judgments.

## What the evidence says about the product today

### Demonstrated strengths

- The product has a focused classroom purpose: curriculum-linked assessment generation and teaching preparation, rather than an attempt to replace every school process at once.
- The teaching workspace brings class, subject, term, and scheme week together. The audit confirmed scope persistence and curriculum context in lesson generation.
- The audit exercised manual lesson-plan creation, AI note generation, note editing and saving, submission, approval, and coverage tracking.
- Teachers can create printable weekly worksheets. The audit downloaded a valid PDF containing the questions. The current form source adds per-question marks, question type, multiple-choice options, and a staff-only answer key.
- Lesson-note PDF and Word export links and session-aware routes now appear in the current source. That is a practical improvement for a teacher who needs paper in class.
- Role distinctions and school governance exist in the product model, including teacher and school administrator roles, invitations, review, and school-scoped access. For a school owner, this is a better starting point than a tool that has no idea how staff responsibilities differ.
- The project includes a mobile navigation pattern, a responsive design intent, durable generation jobs, retry behavior, and a documented backup routine. These are positive engineering choices; the backup and recovery process still needs to be proven operationally with the school that would use it.

### Evidence that limits confidence

The Pass 2 report records a real browser run at desktop and phone widths, including successful workflows and failure scenarios. It also records findings that affect correctness or confidence:

| Area | What the dated audit found | Current evidence and practical meaning |
| --- | --- | --- |
| Worksheet marks | The exported sheet showed the teacher's marks plus an extra hardcoded one-mark label. | Current source has per-question marks and suffix handling, but a new PDF check is needed to verify old and new worksheet records print correctly. |
| Worksheet identity | The audit PDF header did not show the expected subject and class. | This specific finding should be checked against today's export route and an actual downloaded PDF before a school distributes sheets. |
| Action feedback | Teaching actions did not visibly confirm success; messages could show later in the wrong place. | The current main Teaching shell now calls `pop_flash(req)`. This looks addressed in source; verify each action in the browser so confirmation appears immediately and only once. |
| Lesson note portability | The audited screen lacked a note export/print action. | Current source contains PDF and Word links and proxy routes. Recheck real downloads on the deployed build. |
| Reliability under load | The audit observed intermittent 500/504 errors; serial requests later returned 200. | A serial success does not rule out contention or a slow upstream dependency. Test with realistic concurrent use and record a clear recovery path. |
| Exam export | The audit reported that direct student-paper downloads were not available from the detail page and API export calls without bearer authentication returned 401. | Verify the intended teacher path, including the browser session, print/download action, and resulting paper. A raw API probe alone is not the whole user journey. |
| Intermediate tablet width | The audit found horizontal overflow on the exams list at 1024 px. | Check current layout at phone, tablet, and desktop sizes. A narrow phone can be usable while a school tablet remains awkward. |
| Curriculum text | Some scheme-week labels were truncated in the selector. | A teacher needs enough of the topic to choose the correct week; show the whole topic when selecting it. |
| Editing safety | An AI guidance action could replace teacher edits without an unsaved-change warning. | Make preservation of a teacher's own work explicit before regeneration or replacement. |

The audit document is dated and some findings have been remediated since it was written. This report therefore distinguishes **audit evidence** from **current source observations** and does not call a historic defect current unless the present code or a fresh run confirms it.

## The 60-year-old teacher's first experience

Imagine a capable teacher who can use WhatsApp, make calls, take photos, and fill simple forms on an Android phone. She is not afraid of learning, but software jargon, tiny controls, long screens, and unexplained errors will quickly make her feel the tool was built for somebody else.

### First login and finding the right place

If an administrator has already created her account and she receives a working invitation, she can probably sign in with light assistance. The bigger question is what she sees next. The platform has multiple areas for exams, teaching, curriculum, staff, question banks, and administration. A confident computer user may understand those categories; a teacher who came to prepare tomorrow's lesson may ask, “Where should I press first?”

She should not have to learn the product map before getting value. A home screen with two plain choices—**Prepare a lesson** and **Prepare an exam or class exercise**—would match her immediate needs. Less frequent work, such as curriculum management and staff administration, can stay visible to the right people without competing for her attention.

### Creating a lesson plan and note

This is likely the most approachable and valuable workflow once she understands the class, subject, term, and week selections. Curriculum grounding saves her from starting with a blank page, and an AI draft can give her objectives, activities, questions, and teaching resources to work with. Manual creation remains important when she has already prepared her own material or the internet is unreliable.

The friction comes before and after the AI button. She must choose the right class, subject, term, and scheme week; interpret the curriculum wording; understand whether she is creating a plan, drafting a note, saving, submitting, or requesting approval; and decide whether the generated material is good enough to use. “Coverage” and formal review states may make perfect sense to an administrator but feel like office language to a classroom teacher.

A long note in one editing area is tiring on a phone. If she taps a refinement or regenerate control after making personal edits, she needs to know whether her writing will be replaced. She also needs a clear sign that the save worked, then a simple button to get a clean printable copy. The current source's export links are a welcome step, but actual downloads should be verified on her device and on the school's printer.

**Judgment:** With class and subject defaults remembered, visible examples, an obvious “Draft my lesson note” action, a reliable save indicator, and paper/Word export, she could likely learn this workflow in one guided session and repeat it with increasing independence. Without that help, she may complete the first AI draft but remain unsure whether it is saved, approved, or ready to teach from.

### Creating a class exercise

The current worksheet form is more structured than a single free-text list: the source shows fields for question type, question text, marks, options, and staff answer key, with an add-question control. That structure helps quality, but on a phone each question becomes a set of fields. Adding ten questions may require a lot of scrolling, tapping, and typing, particularly for someone typing on a small keyboard.

She may not know what “MCQ” means, whether the answer key will be shown to learners, or whether the marks she enters add up to the total she expects. Clear everyday wording, a worked example, a visible running total, and a preview of the student copy would reduce this anxiety. A teacher should be able to start with a plain paper or import/reuse a question, then add detail only where needed.

**Judgment:** A short exercise should be manageable after demonstration. A long worksheet or a paper with mixed formats is likely to feel laborious on a phone unless the product supports reusable questions, cloning, voice-friendly entry, or a larger-screen workflow.

### Creating an examination

This is the hardest task for the persona. An examination is not just a collection of questions: teachers must balance topics, marks, difficulty, sections, instructions, answer keys, and a layout that prints correctly. The system has powerful generation and review capabilities, but that creates decisions and review responsibility. AI can save typing, but it does not remove the teacher's duty to confirm that questions are correct, age-appropriate, curriculum-aligned, and fairly marked.

She needs a guided path that begins with a familiar request: “Which class and subject? Which term or topics? How many questions? What total mark?” Defaults should cover a normal paper; advanced choices should be available when she wants them. Before printing, she should see the student paper and marking guide, know what is included, and have an easy way to flag a questionable question. If a school requires principal approval, the status and next step should be explained in plain language.

**Judgment:** She is unlikely to create a full exam independently the first time without support. She could become comfortable with a consistent, guided workflow after practice, but should not be expected to operate a complex editor as if she were a software administrator.

### General use on phone and with weak connectivity

The product targets Android phones and has responsive navigation. The audit reported clean page widths at the two phone sizes it checked, but that does not by itself prove comfortable touch targets, readable text, smooth use on a small screen, or operation on slow data. Generating AI content depends on a network and external services, so the teacher needs an honest waiting state and the assurance that waiting, navigating away, or refreshing will not lose work or create duplicate work.

Her confidence is likely to come from familiar routines: saved work visible in a list, the current class and subject written at the top, a clear “Saved” status, a usable print/share action, and a human contact if something fails. She should not have to interpret a stack trace, a blank page, a vague red banner, or a status such as “504”.

## Principal or school-owner view

I have tried school systems that looked promising but became difficult to operate or unreliable after adoption. I will not be persuaded by the number of features, the technology stack, or a polished demo alone. I want to know whether teachers will actually use this next week, whether their printed papers will be right, and who will help when something goes wrong.

### Would I try it?

**Yes, conditionally, as a limited and supported pilot.** The niche direction is a strength: curriculum-linked lesson preparation and assessment are concrete problems that a school can evaluate quickly. The teaching and assessment workflows fit existing school routines, and the school has a chance to retain teacher review and principal oversight.

I would not immediately replace paper files, lesson-note books, existing exam templates, or the school's wider management system. I would keep the old path available through the pilot and compare the time and quality of real work. I would consider expansion only after teachers of different ages and confidence levels complete real tasks repeatedly, printed materials are checked, and the school sees reliable recovery from failures.

### What I would look for before starting

1. **A specific, bounded promise.** What does SkuPhase do for my school today? Which classes and subjects are supported by verified curriculum data? The README says the curriculum covers Pre-Nursery through Primary 6 and that JSS/SSS data is planned. I would require this scope to be clearly stated in sales material and in the interface. A dropdown option must not be mistaken for curriculum-backed coverage.
2. **Correct printed work.** I would inspect real exam papers, marking guides, lesson notes, and worksheets with our own school name, class, subject, term, marks, diagrams, and equations. A wrong class label or mark allocation can embarrass a teacher and damage trust immediately.
3. **A live teacher trial, not a founder demonstration.** I would ask at least one less-confident teacher to create a lesson note and printable exercise using only the instructions we plan to provide. I would watch where they stop, guess, ask for help, or make an error.
4. **Reliability under the school's actual pattern.** I want several teachers signed in, saving, generating, and exporting around a busy period. I want records of failures, wait times, retry outcomes, and confirmation that work was not lost.
5. **A clear support and recovery arrangement.** Who do I call or message? During which hours? How quickly will someone respond? What does the teacher do if the network or AI provider is down before class?
6. **School control and staff onboarding.** Can I invite a teacher, correct a mistaken role, remove access when they leave, and understand who can view, edit, approve, or export school work?
7. **Privacy and ownership answers.** What student or staff information is stored? Are student names needed? Who can access school-generated content? How long is it retained? What happens when we stop using the product? These answers should be short, written, and understandable.
8. **Backup and restore evidence.** A backup job is not enough: I want to know when the last backup completed and see a restoration rehearsal that proves the school can recover its work.
9. **Total cost and constraints.** State the pilot price, what counts as a generation, any monthly caps, data costs, printer requirements, and likely support costs before we begin.
10. **A simple success measure.** Agree on baseline time and quality: preparation time, correction count, printing problems, weekly active teachers, and teacher confidence. Do not claim success solely because accounts were created.

### Conditions I would set for a pilot

- Start with one or two willing departments or a small group of teachers and a named school champion.
- Select a short list of curriculum-covered classes and subjects, and test both lesson-note and assessment work.
- Keep each teacher's existing method available during the comparison period.
- Use fictional or minimal learner information; do not upload identifiable student data unless it is necessary and the school's data rules are clear.
- Require a teacher to review every AI-generated question and note before classroom use.
- Check sample PDFs on an actual Android phone and school printer before sharing them with students.
- Agree who provides support, how incidents are reported, and what teachers should do during an outage.
- Review pilot measures together after two to four weeks and make continuation optional for the school.

## What would make SkuPhase much more beneficial

### Priority 0: Make the existing promise dependable

1. **Re-run the critical end-to-end checks on the current build.** Create and export worksheets with varied marks and verify the displayed total and each mark. Confirm subject, class, term, and school identity in the actual PDF. Generate, edit, save, and export a lesson note. Create, review, approve, and export an exam through the teacher-facing session, not just by calling an API directly. Test with multiple users and slow/failing upstream responses.
2. **Make action feedback immediate and unmistakable.** Saving, submitting, approving, exporting, and failing must each produce one message in context. Never silently discard a confirmation or show it on an unrelated page later.
3. **Protect teacher work.** Warn before replacing unsaved text. Keep a recoverable draft if a session expires or a phone browser reloads. Display “Saved just now” with a timestamp or equivalent signal.
4. **Handle slowness as a normal situation.** Show that generation is in progress, explain that the teacher can wait safely, and provide a retry path that does not lose the draft or duplicate the output. Display a partial workspace with a useful message if one data source is down.
5. **Make output quality review part of the workflow.** Offer a clear student copy and staff marking guide, a final checklist for class/subject/date/marks, and a large, legible print preview. Allow teachers to report a bad question and revise only that question.

### Priority 1: Design around the teacher's phone and working day

1. **Add a task-first teacher home.** Put “Prepare a lesson,” “Create an exercise,” and “Prepare an exam” first. Show recent work, drafts needing attention, and today's likely next action. Put admin and curriculum maintenance behind role-aware sections.
2. **Create a guided standard path.** Ask for class, subject, term/week, purpose, and desired length in everyday language; set sensible defaults; show advanced options only when requested. Preserve an equally visible manual path for teachers who already have questions.
3. **Break long work into short stages.** Let a teacher complete scope, questions or lesson sections, review, and print in separate steps. Show progress and provide Back/Continue without losing entries.
4. **Use recognizable school language.** Prefer “Mark this week as taught” to “coverage tracking,” “Send to the principal for review” to an unexplained workflow state, and define terms such as answer key, objective question, and scheme week where they first appear.
5. **Use the actual curriculum wording without hiding it.** Show complete week/topic names and a short explanation of how selected weeks affect generated content. If an option is unavailable for a class, explain why and suggest what the teacher can choose.
6. **Reduce repeated typing.** Remember the teacher's usual class, subject, and term; provide reusable school-approved lesson and exam templates; allow teachers to copy a prior paper and edit it; keep autosaved drafts.
7. **Make phone operation forgiving.** Use large touch targets, strong contrast, clear field labels, short forms, adequate spacing, and no sideways scrolling. Test the common low-cost Android viewport, browser zoom, keyboard overlap, and slow mobile data.
8. **Make language and reading support practical.** Use short sentences and examples. Consider optional voice dictation for lesson notes and question entry, and carefully designed local-language explanations or help if pilot teachers ask for them.

### Priority 2: Increase school value after the core is trusted

1. **Teacher and school collaboration:** shared approved templates, department question collections, safe copying between terms, review comments, and clear ownership of school materials.
2. **A useful preparation calendar:** upcoming lesson plans and assessment deadlines, missed weeks, and a simple view of what is ready, without turning the product into a large student-information system.
3. **Curriculum coverage reports with context:** show which topics are planned, taught, or reviewed, who updated them, and when. Let the school distinguish teacher self-report from administrator confirmation.
4. **Offline and weak-network resilience:** allow reading and editing saved drafts offline where feasible, then sync safely; cache curriculum reference material; clearly label AI generation as requiring connection.
5. **School-friendly support and administration:** a short guided setup, teacher onboarding cards, searchable help, a visible support route, staff access management, and a simple incident/maintenance status page.
6. **Transparent usage and costs:** show generation allowance, remaining usage, and a plain-language explanation of what a generation consumes. Alert an administrator before a limit blocks work.
7. **Curriculum scope expansion only with verified content:** add JSS/SSS or additional boards after sourcing and checking the actual schemes and learning objectives. Do not present ungrounded generation as equivalent to curriculum-aligned output.

### What I would deliberately avoid adding yet

I would not rush to add fees, attendance, payroll, student records, parent messaging, transport, inventory, or a broad “all-in-one school management” claim just to compete with older platforms. Those features expand privacy, support, and reliability obligations and could distract from the current niche. SkuPhase becomes more valuable first by making its core teaching and exam work safe, correct, printable, and easy for ordinary teachers.

## Recommended implementation order

| Order | Work | Why it comes first | Evidence to close it |
| --- | --- | --- | --- |
| 1 | Current-build regression of lesson, worksheet, and exam journeys | Confirms the fixes and exposes any remaining correctness errors before adoption. | Browser-run task records; PDFs/DOCX inspected; no lost input; correct marks and school/class metadata. |
| 2 | Reliability and recovery under realistic concurrent use | An unavailable or ambiguous system recreates the owner's past failures. | Load scenario, error rates and latency, safe retry, no duplicate records, and documented recovery. |
| 3 | Teacher-observed usability sessions on Android | Replaces assumptions with observed friction from the actual target users. | Several teachers complete defined tasks without coaching; record task completion, help requests, errors, and confidence. |
| 4 | Guided teacher home and progressive disclosure | Reduces the amount a first-time user must understand. | First-use tests show teachers can find and finish their common task. |
| 5 | School pilot controls, support, privacy, and restore rehearsal | Gives a cautious owner an accountable way to try the service. | Written pilot terms, named support contact, access checklist, privacy answers, and a successful restore drill. |
| 6 | Collaboration, calendar, offline improvements, and curriculum expansion | Adds more value after basic confidence and repeat use are established. | Pilot feedback demonstrates demand and the curriculum data is verified. |

## Final answer to the two questions

**For the teacher:** I would say, “This system can help you prepare lessons and papers, and you do not need to be a computer expert. The first time, let someone show you the simple path. Start with one lesson or exercise, check the result, save it, and print it. Do not feel you must use every option.” With a guided path and reliable feedback, she could become an independent repeat user. In its full current breadth, she is more likely to need an initial demonstration and occasional support, especially for exams and phone-based editing.

**For the principal or owner:** I would try SkuPhase, but only in a small pilot with the old method still available. I would require proof that the generated and exported materials are correct, teachers can complete common tasks without technical help, failures do not lose work, and the school knows how to get support and restore data. If those conditions are met and teachers return to it voluntarily, the niche is credible and useful. If papers are wrong, feedback is unclear, or the service fails during busy periods, a school that has already lost trust in software will return to paper quickly.

The most beneficial next step is not to widen the feature list. It is to **close the current output/reliability checks and observe real teachers using the guided core workflows**. That evidence will show whether SkuPhase is ready to become a habit at school, rather than simply a capable product in a demonstration.

## Source basis and limitations

- SkuPhase source and product documentation in this checkout, including `README.md`, `FRONTEND_SPEC.md`, `TEACHER_WORKFLOW_UX_IMPLEMENTATION_PLAN.md`, `SYSTEM_AUDIT_AND_ROADMAP.md`, the Teaching frontend and worksheet export code.
- `skuphase_audit_pass2/VISUAL_E2E_AUDIT_PASS_2.md`, a dated Playwright/browser and PDF audit describing tested routes, viewports, successful tasks, and findings. The report itself says some Pass 1 items were rechecked rather than fully retested.
- Current-source spot checks made for this assessment. No new tests, browser run, live deployment check, or teacher interviews were performed for this document.
- The persona and principal's willingness are informed judgments, not measured user research or a guarantee of adoption.
