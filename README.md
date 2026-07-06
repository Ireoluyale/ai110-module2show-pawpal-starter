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

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
