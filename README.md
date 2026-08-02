# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## ✨ Features

The scheduling engine (`pawpal_system.py`) implements these algorithms:

- **Sorting by time** — orders tasks by time of day (earliest first) using a
  parsed numeric key (minutes since midnight), so `"9:00"` sorts before
  `"18:00"` instead of after it.
- **Sorting by priority** — orders tasks highest priority first, with time of
  day as the tie-breaker (and vice-versa when sorting by time).
- **Filtering** — narrows tasks by pet name, completion status, or both, via a
  single composable method.
- **Today's schedule** — returns only pending tasks due on or before today,
  time-ordered, so tomorrow's freshly spawned occurrences stay out of view.
- **Conflict warnings** — flags tasks that clash on the same date and time,
  catching both a single pet double-booked and two pets needing attention at
  once; also available as a crash-safe, human-readable warning string.
- **Daily / weekly recurrence** — completing a recurring task automatically
  spawns its next occurrence with the due date advanced (+1 day / +7 days).
- **Grouping** — buckets tasks by category or by pet, each bucket sorted.
- **🤖 Agentic AI planner** — Claude plans the day, checks its own work against
  the Scheduler's real conflict/time-budget logic, revises, and submits a
  validated plan (see [AI Care Planner](#-ai-care-planner-agentic-ai-feature)).

## 🤖 AI Care Planner (agentic AI feature)

`ai_planner.py` adds the project's AI feature: an **agentic workflow** where the
AI can *plan, act, and check its own work* before committing to an answer.

**How the agent loop works** (`AIPlanner.plan_day`):

1. **Plan** — Claude reads the goal: build today's plan within the owner's daily
   time budget, avoid two tasks booked at the same time, respect task priority.
2. **Act** — it calls tools that read the *live* `Scheduler`: `inspect_schedule`
   (today's pending tasks + estimated minutes), `check_conflicts`
   (`Scheduler.check_conflicts`), and `validate_plan`.
3. **Check its own work** — `validate_plan` re-runs the real conflict detection
   and time-budget math on the AI's proposed ordering and returns `PASS` or
   `FAIL: …`. The AI is required to iterate until it gets a `PASS`.
4. **Submit** — only then does it call `submit_plan`, and that validated ordering
   becomes the schedule the app displays.

This is **fully integrated, not a bolt-on**: the AI's tools call the same domain
methods the rest of PawPal+ uses, and its output *is* the plan shown in the UI.

**Reliability & guardrails**

- **Graceful fallback** — with no API key (or on any API error), a deterministic
  rule-based planner runs instead, so the app always produces a plan.
- **Logging** — every tool call and outcome is logged to `pawpal_ai.log`.
- **Bounded loop** — the agentic loop is capped (`MAX_TOOL_ROUNDS`) and the AI's
  submitted task IDs are re-verified against real pending tasks before use.

### System diagram

See [`diagrams/system_diagram.md`](diagrams/system_diagram.md) for a Mermaid
diagram of the components, the input → process → output flow, and where the AI's
results get checked (self-validation, human review, and the test suite).

### Sample interactions

Each example is an **input** (pets, tasks, and the owner's daily time budget) and
the **plan the system returns**. The rule-based outputs below are copied verbatim
from `python ai_planner.py` (no key needed, so they're reproducible); the
Claude-powered output is representative of what the agent submits once
`ANTHROPIC_API_KEY` is set.

**Example 1 — same-time conflict (budget 3h).** Rex needs brushing at 09:00, but
Milo's allergy meds are also at 09:00 and are higher priority. The planner keeps
the higher-priority task in that slot and defers the other.

```
Input:  Rex  08:00 Morning walk (walk, medium)
        Milo 09:00 Allergy meds (medication, high)
        Rex  09:00 Brush coat (grooming, low)
        Rex  18:00 Evening walk (walk, medium)

Output (⚙️ rule-based):
  Rule-based plan: fit 3 task(s) into the owner's 180-minute budget (65 min
  used), highest priority first. Resolved same-time clashes by keeping the
  higher-priority task. 1 task(s) deferred (conflict or over budget).

  Today (65 min):
    08:00  Rex    Morning walk (walk, p2)
    09:00  Milo   Allergy meds (medication, p1)
    18:00  Rex    Evening walk (walk, p2)
  Deferred:
    09:00  Rex    Brush coat (p3)     ← lost the 09:00 slot to Milo's meds
```

**Example 2 — over budget (budget 0.5h).** Three tasks won't fit in 30 minutes,
so the planner keeps the highest-priority task and defers the rest.

```
Input:  Rex 07:30 Refill food  (feeding, medium)
        Rex 08:00 Morning walk (walk, high)
        Rex 18:00 Evening walk (walk, low)

Output (⚙️ rule-based):
  Rule-based plan: fit 1 task(s) into the owner's 30-minute budget (30 min used),
  highest priority first. 2 task(s) deferred (conflict or over budget).

  Today (30 min):
    08:00  Rex    Morning walk (walk, p1)
  Deferred:
    07:30  Rex    Refill food (p2)
    18:00  Rex    Evening walk (p3)
```

**Example 3 — the same conflict, with Claude enabled** (`ANTHROPIC_API_KEY` set).
Same input as Example 1. The agent calls `inspect_schedule` and `check_conflicts`,
drafts a plan, calls `validate_plan` (which FAILs because both 09:00 tasks are
present), revises to drop the lower-priority one, gets a PASS, then `submit_plan`.
The plan is the same, but it comes with the agent's own explanation:

```
Output (🤖 Planned by Claude):
  "I kept Milo's allergy medication at 09:00 since medication is high priority
   and time-sensitive, and moved Rex's coat brushing off today's plan because it
   clashed with that slot and is the lowest-priority item. The two walks and the
   meds fit comfortably in your 3-hour budget (65 of 180 minutes), so everything
   except the grooming is scheduled."

  Today (65 min):  08:00 Rex Morning walk · 09:00 Milo Allergy meds · 18:00 Rex Evening walk
  Deferred:        Rex Brush coat (conflict with higher-priority meds)
```

> The two paths reach the same schedule here — by design, since the AI validates
> against the *same* budget/conflict rules the fallback uses. Claude adds natural-
> language reasoning and handles fuzzier trade-offs; the fallback guarantees a
> sensible plan even with no key.

### Design decisions & trade-offs

- **Agentic tool-use loop, not a single prompt.** A one-shot "here are the tasks,
  give me a plan" prompt would let the model *assert* a schedule without any check
  that it's valid. Instead the agent must call `validate_plan` and get a `PASS`
  before it can `submit_plan`. **Trade-off:** more API round-trips (higher latency
  and cost) in exchange for plans that are actually checked against real rules.
- **Tools wrap the real `Scheduler`.** `inspect_schedule`, `check_conflicts`, and
  `validate_plan` read the same domain objects and call the same methods
  (`Scheduler.find_conflicts`, the owner's `hours_available_daily`) as the rest of
  the app. The AI can't reason over a stale or invented copy of the data — there's
  one source of truth. This is what makes the feature *integrated* rather than a
  bolt-on.
- **A validator gate is the "check its own work" step.** Making `validate_plan`
  return `FAIL: …` with specifics (which id is unknown, how far over budget, which
  slot clashes) turns self-correction into a concrete loop the model can act on,
  instead of hoping it self-audits.
- **Durations estimated by category, not stored on `CareTask`.** Adding a
  `duration` field would have changed the domain model and its tests. Estimating
  by category (`walk`≈30, `medication`≈5, …) gives the planner a real time budget
  to reason about with zero changes to `pawpal_system.py`. **Trade-off:** the
  minutes are approximations, not exact durations.
- **Deterministic rule-based fallback.** The AI path is non-deterministic and
  needs a key, network, and credits. A deterministic fallback means the app always
  works, costs nothing to demo, is fully reproducible, and — importantly — gives
  the test suite a stable surface to assert against. **Trade-off:** two code paths
  to maintain, kept in sync by making both obey the same budget/conflict rules.
- **Default model `claude-opus-5`.** Chosen for reasoning quality; it's a single
  `MODEL` constant in `ai_planner.py`, so swapping to `claude-sonnet-5` or
  `claude-haiku-4-5` for lower cost is a one-line change.

### Testing summary — what worked, what didn't, what I learned

**What worked**
- The **deterministic fallback is fully unit-tested** (`tests/test_ai_planner.py`,
  5 tests): over-budget deferral, same-time conflict resolution, the empty-schedule
  case, category-based duration estimates, and that no key means the fallback runs.
  These pass with no network and no key, so CI stays green.
- A **headless Streamlit smoke test** (`streamlit.testing.v1.AppTest`) renders the
  app and clicks "Generate AI plan" with 0 exceptions — it exercises the real UI
  wiring, not just the module in isolation.

**What didn't work at first (and how it was fixed)**
- The app first crashed on the AI section with a `NameError`: `INT_TO_PRIORITY`
  was defined *after* the new section used it. The `AppTest` smoke test caught it;
  the fix was moving that definition up next to `PRIORITY_TO_INT`.
- An early import pulled a symbol (`INT_TO_PRIORITY`) from `ai_planner` that didn't
  exist there — a reminder to import from where a name actually lives.

**What I learned**
- **You can't unit-test a live LLM deterministically** — it needs a key, costs
  money, and its wording varies. The lesson was to put the *checkable logic* (the
  budget/conflict rules) in code the tests can pin down, and have the AI validate
  against that same logic. The guardrails (`validate_plan` + the fallback) double
  as the testable surface.
- **Design the AI feature around a deterministic core.** Because the fallback and
  the AI obey identical rules, a passing fallback test also documents what a valid
  AI plan must satisfy.

Run the AI-specific tests with:

```bash
pytest tests/test_ai_planner.py -v
```

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Enable the AI planner (optional but recommended)

The app runs without a key (it uses the rule-based fallback). To enable the real
Claude-powered agent, set your Anthropic API key:

```bash
# macOS / Linux
export ANTHROPIC_API_KEY=sk-ant-...

# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Get a key at <https://console.anthropic.com>. The default model is `claude-opus-5`;
change `MODEL` in `ai_planner.py` to `claude-sonnet-5` or `claude-haiku-4-5` for
lower cost.

### Run

```bash
# Streamlit app (includes the AI Care Planner section)
python -m streamlit run app.py

# Or the CLI demo of the planner (uses the fallback if no API key is set)
python ai_planner.py
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:


PS C:\Users\ireol\ai110-module2show-pawpal-starter> & C:/Users/ireol/AppData/Local/Programs/Python/Python313/python.exe c:/Users/ireol/ai110-module2show-pawpal-starter/main.py
============================================
Today's Schedule
============================================
07:30  Milo   Refill food bowl (feeding)
08:00  Rex    Morning walk (walk)
09:00  Milo   Give allergy meds (medication)
18:00  Rex    Evening walk (walk)
--------------------------------------------
4 task(s) remaining today.

```
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
S C:\Users\ireol\ai110-module2show-pawpal-starter> python -m pytest
================================================ test session starts =================================================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\ireol\ai110-module2show-pawpal-starter
plugins: anyio-4.14.0
collected 5 items                                                                                                     

tests\test_pawpal.py .....                                                                                      [100%]

================================================= 5 passed in 0.03s ==================================================
```

## 📐 Smarter Scheduling

The scheduling logic lives in `pawpal_system.py`. Each feature below names the
method that implements it.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `sort_tasks()` | Orders by time of day (earliest first) |
| Filtering | `Scheduler.filter_tasks()` | By pet name and/or completion status |
| Conflict detection | `Scheduler.find_conflicts()`, `Scheduler.check_conflicts()` | Flags tasks at the same date + time |
| Recurring tasks | `CareTask.mark_complete()`, `CareTask.next_occurrence()` | Completing a daily/weekly task spawns the next one |

### Sorting behavior — `Scheduler.sort_by_time()`

Tasks can be added in any order; the scheduler returns them ordered by time of
day. Sorting keys on a **parsed numeric value** (`CareTask.minutes`, minutes
since midnight) rather than the raw `"HH:MM"` string, so ordering stays correct
even for non–zero-padded times like `"9:00"` (a plain string sort would place
`"9:00"` after `"18:00"`).

- `Scheduler.sort_by_time()` — every task, earliest first.
- `sort_tasks(tasks, by="time"|"priority")` — the shared helper used throughout.
  Uses composite keys: `"time"` breaks ties by priority, `"priority"` breaks
  ties by time.
- `Scheduler.get_todays_schedule()` — pending tasks due on/before today, time-sorted.

### Filtering behavior — `Scheduler.filter_tasks()`

A single composable method filters by **pet name**, **completion status**, or
both:

```python
scheduler.filter_tasks(pet_name="Milo")                 # all of Milo's tasks
scheduler.filter_tasks(completed=False)                 # everything still pending
scheduler.filter_tasks(pet_name="Rex", completed=True)  # Rex's completed tasks
```

Both arguments default to `None` (= "don't filter on this"), which is why
`completed=False` can be distinguished from "no status filter". Results come
back time-sorted.

### Conflict detection — `Scheduler.find_conflicts()` / `check_conflicts()`

Two tasks conflict when they share the same **due date and time of day**. The
grouping ignores which pet owns each task, so it catches both:

- the **same pet** double-booked (two of Rex's tasks at 18:00), and
- **different pets** needing attention at once (Rex + Milo both at 09:00).

Completed tasks are ignored (they no longer compete for the owner's time).

- `find_conflicts()` — returns structured groups (`list[list[CareTask]]`) for
  code that needs to act on conflicts.
- `check_conflicts()` — a lightweight wrapper that returns a **warning string**
  (`[!] ...`) or an all-clear (`[OK] No scheduling conflicts.`). It is wrapped
  in `try/except` so it reports problems instead of crashing the program.

### Recurring task logic — `CareTask.mark_complete()` / `next_occurrence()`

Each `CareTask` has a `frequency` (`"daily"`, `"weekly"`, or a one-off value)
and a `due_date`. When a **recurring** task is marked complete, the next
occurrence is created automatically:

- `CareTask.mark_complete()` — marks the task done and, if it recurs and belongs
  to a pet, adds a fresh incomplete copy for the next date to that pet. Returns
  the new task (or `None` if nothing was spawned).
- `CareTask.next_occurrence()` — builds that copy: a new unique id, `completed`
  reset to `False`, and `due_date` advanced by the frequency (`daily` → +1 day,
  `weekly` → +7 days).

One-off tasks don't recur, and completing an already-completed task does nothing
(no duplicate spawns).

## 🚶 Demo Walkthrough

### The interface

Launch the Streamlit app with `streamlit run app.py`. The page is organized top
to bottom into a few actions:

- **Add a Pet** — enter a name, species, breed, age, and weight, then submit.
  Added pets appear in a live table showing each pet's profile and its task
  count.
- **Add a Care Task** — pick one of your pets, then set the task's description,
  time (`HH:MM`), category (feeding / walk / medication / grooming), priority
  (low / medium / high), and frequency (daily / weekly / monthly).
- **Build Schedule** — choose how to organize everything:
  - *Priority (highest first)* — every task, most important on top.
  - *Time (earliest first)* — every task ordered by time of day.
  - *Group by pet* — one table per pet.
  A live **conflict banner** sits above the button: green when the day is clear,
  yellow listing every clash when two tasks land on the same date and time.
  Results render as clean tables with a human-readable priority label.

### Example workflow

1. **Add a pet** — create "Rex" (dog, Labrador).
2. **Schedule tasks** — add Rex's "Morning walk" at `08:00` and "Evening walk"
   at `18:00`, both daily, high priority.
3. **Add a second pet and a clashing task** — add "Milo" (cat) with "Give
   allergy meds" at `18:00`.
4. **Generate the schedule** — pick *Time (earliest first)* and click
   **Generate schedule**. The tasks come back time-ordered (08:00 → 18:00)
   regardless of the order you entered them.
5. **Read the conflict warning** — because Rex's evening walk and Milo's meds
   both fall at `18:00`, the yellow banner flags a "different pets" conflict so
   you can rebalance the day.

### Key Scheduler behaviors on display

- **Sorting** — tasks entered out of order are returned time- or priority-sorted
  (`sort_by_time()`, `get_tasks_by_priority()`), keyed on parsed minutes so
  `"9:00"` never sorts after `"18:00"`.
- **Conflict warnings** — `check_conflicts()` powers the banner, catching both
  same-pet double-bookings and cross-pet clashes.
- **Grouping** — the *Group by pet* view uses `tasks_by_pet()`.
- **Recurrence** — in the CLI demo, completing a daily task auto-spawns the next
  day's occurrence (`mark_complete()` → `next_occurrence()`).

### Sample CLI output (`python main.py`)

```text
============================================
Today's Schedule
============================================
08:00  Rex    Morning walk (walk)
09:00  Milo   Give allergy meds (medication)
18:00  Rex    Evening walk (walk)
21:00  Milo   Bedtime treat (feeding)
--------------------------------------------
4 task(s) remaining today.

============================================
Filtering demo
============================================

All of Milo's tasks:
--------------------------------------------
  07:30  Milo   Refill food bowl     [done]
  07:30  Milo   Refill food bowl     [pending]
  09:00  Milo   Give allergy meds    [pending]
  21:00  Milo   Bedtime treat        [pending]

Still pending:
--------------------------------------------
  07:30  Milo   Refill food bowl     [pending]
  08:00  Rex    Morning walk         [pending]
  09:00  Milo   Give allergy meds    [pending]
  18:00  Rex    Evening walk         [pending]
  21:00  Milo   Bedtime treat        [pending]

Already completed:
--------------------------------------------
  07:30  Milo   Refill food bowl     [done]

Rex's pending tasks:
--------------------------------------------
  08:00  Rex    Morning walk         [pending]
  18:00  Rex    Evening walk         [pending]

============================================
Recurring-task demo
============================================
Completing: Morning walk (due 2026-07-06, daily)
  -> auto-created task #7: Morning walk due 2026-07-07 (still pending)

Rex's tasks now:
--------------------------------------------
  08:00  Rex    Morning walk         [done]
  08:00  Rex    Morning walk         [pending]
  18:00  Rex    Evening walk         [pending]

============================================
Conflict-detection demo
============================================
[!] 2 scheduling conflict(s) found:
  - 09:00 (different pets) -> Milo: Give allergy meds, Rex: Brush coat
  - 18:00 (same pet) -> Rex: Give joint supplement, Rex: Evening walk
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
