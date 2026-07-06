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

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
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
