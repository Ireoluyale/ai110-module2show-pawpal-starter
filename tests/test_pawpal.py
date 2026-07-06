"""Basic tests for the PawPal+ domain classes."""

import os
import sys

# Allow importing pawpal_system from the project root when tests run from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date, timedelta

from pawpal_system import Pet, CareTask, Owner, Scheduler


def make_task(task_id: int = 1) -> CareTask:
    return CareTask(
        task_id=task_id,
        description="Morning walk",
        time="08:00",
        frequency="daily",
        category="walk",
        priority=1,
    )


def make_scheduler(*pets: Pet) -> Scheduler:
    """Wrap the given pets under a single owner in a fresh Scheduler."""
    owner = Owner(
        owner_id=1, name="Alex", hours_available_daily=4.0, reminders_enabled=True
    )
    for pet in pets:
        owner.add_pet(pet)
    scheduler = Scheduler()
    scheduler.add_owner(owner)
    return scheduler


def test_mark_complete_changes_status():
    """mark_complete() should flip a task from incomplete to complete."""
    task = make_task()
    assert task.completed is False  # starts pending

    task.mark_complete()

    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    """Adding a task to a Pet should grow that pet's task list by one."""
    pet = Pet(pet_id=1, name="Rex", species="dog", breed="Lab", age=3, weight=30.0)
    assert len(pet.tasks) == 0

    pet.add_task(make_task())

    assert len(pet.tasks) == 1


def test_sort_returns_tasks_in_chronological_order():
    """sort_by_time() should order tasks earliest-first, comparing numerically.

    The out-of-order times (and "9:00" without a leading zero) would sort
    wrongly under a raw string comparison, so this also guards the numeric key.
    """
    pet = Pet(pet_id=1, name="Rex", species="dog", breed="Lab", age=3, weight=30.0)
    times = ["18:00", "09:00", "08:00", "12:30"]
    for i, t in enumerate(times, start=1):
        pet.add_task(
            CareTask(
                task_id=i,
                description=f"task {i}",
                time=t,
                frequency="once",
                category="walk",
                priority=1,
            )
        )
    scheduler = make_scheduler(pet)

    ordered = scheduler.sort_by_time()

    assert [t.time for t in ordered] == ["08:00", "09:00", "12:30", "18:00"]


def test_completing_daily_task_creates_next_days_occurrence():
    """Marking a daily task complete should spawn a fresh task due the next day."""
    pet = Pet(pet_id=1, name="Rex", species="dog", breed="Lab", age=3, weight=30.0)
    today = date.today()
    task = CareTask(
        task_id=1,
        description="Morning walk",
        time="08:00",
        frequency="daily",
        category="walk",
        priority=1,
        due_date=today,
    )
    pet.add_task(task)

    spawned = task.mark_complete()

    # Original is now done; a brand-new, incomplete occurrence exists.
    assert task.completed is True
    assert spawned is not None
    assert spawned.completed is False
    assert spawned.due_date == today + timedelta(days=1)
    assert spawned.task_id != task.task_id
    assert len(pet.tasks) == 2
    assert spawned in pet.tasks


def test_scheduler_flags_tasks_at_duplicate_times():
    """find_conflicts() should group tasks sharing the same date and time."""
    today = date.today()
    rex = Pet(pet_id=1, name="Rex", species="dog", breed="Lab", age=3, weight=30.0)
    milo = Pet(pet_id=2, name="Milo", species="cat", breed="Tabby", age=2, weight=4.0)
    # Rex and Milo both need attention at 08:00 today -> one conflict.
    rex.add_task(
        CareTask(
            task_id=1, description="Walk", time="08:00", frequency="daily",
            category="walk", priority=1, due_date=today,
        )
    )
    milo.add_task(
        CareTask(
            task_id=2, description="Feed", time="08:00", frequency="daily",
            category="feeding", priority=2, due_date=today,
        )
    )
    # A non-clashing task at a different time should not be flagged.
    rex.add_task(
        CareTask(
            task_id=3, description="Evening walk", time="18:00", frequency="daily",
            category="walk", priority=1, due_date=today,
        )
    )
    scheduler = make_scheduler(rex, milo)

    conflicts = scheduler.find_conflicts()

    assert len(conflicts) == 1
    clashing = conflicts[0]
    assert len(clashing) == 2
    assert {t.task_id for t in clashing} == {1, 2}
    assert all(t.time == "08:00" for t in clashing)
