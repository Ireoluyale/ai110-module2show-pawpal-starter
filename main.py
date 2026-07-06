"""PawPal+ demo script.

Builds a small owner/pet/task setup and prints today's schedule.
"""

from pawpal_system import Owner, Pet, CareTask, Scheduler


def build_demo() -> Scheduler:
    """Create an owner with two pets and a few tasks, wired into a Scheduler."""
    owner = Owner(
        owner_id=1,
        name="Ada",
        hours_available_daily=2.0,
        reminders_enabled=True,
    )

    rex = Pet(pet_id=1, name="Rex", species="dog", breed="Labrador", age=3, weight=30.0)
    milo = Pet(pet_id=2, name="Milo", species="cat", breed="Tabby", age=5, weight=4.5)

    # Deliberately added OUT of chronological order (18:00 before 08:00, etc.)
    # to prove the sorting methods reorder them rather than relying on input order.
    rex.add_task(CareTask(2, "Evening walk", "18:00", "daily", "walk", priority=2))
    milo.add_task(CareTask(3, "Give allergy meds", "09:00", "daily", "medication", priority=1))
    rex.add_task(CareTask(1, "Morning walk", "08:00", "daily", "walk", priority=2))
    milo.add_task(CareTask(5, "Bedtime treat", "21:00", "daily", "feeding", priority=3))
    milo.add_task(CareTask(4, "Refill food bowl", "07:30", "daily", "feeding", priority=1))

    owner.add_pet(rex)
    owner.add_pet(milo)

    scheduler = Scheduler()
    scheduler.add_owner(owner)

    # Mark one task done so the completion-status filter has something to show.
    scheduler.complete_task(4)  # Milo's "Refill food bowl"
    return scheduler


def print_todays_schedule(scheduler: Scheduler) -> None:
    """Print all pending tasks across pets, ordered by time of day."""
    schedule = scheduler.get_todays_schedule()

    print("=" * 44)
    print("Today's Schedule")
    print("=" * 44)

    if not schedule:
        print("Nothing left to do today. \U0001F415")
        return

    for task in schedule:
        print(f"{task.time}  {task.pet_name:<5}  {task.description} ({task.category})")

    print("-" * 44)
    print(f"{len(schedule)} task(s) remaining today.")


def print_task_list(title: str, tasks) -> None:
    """Print a labelled list of tasks (used to show filtering results)."""
    print(f"\n{title}")
    print("-" * 44)
    if not tasks:
        print("  (none)")
        return
    for task in tasks:
        status = "done" if task.completed else "pending"
        print(f"  {task.time}  {task.pet_name:<5}  {task.description:<20} [{status}]")


def main() -> None:
    scheduler = build_demo()

    # Sorting: tasks were added out of order; these come back time-ordered.
    print_todays_schedule(scheduler)

    # Filtering: by pet name, and by completion status.
    print("\n" + "=" * 44)
    print("Filtering demo")
    print("=" * 44)
    print_task_list("All of Milo's tasks:", scheduler.filter_tasks(pet_name="Milo"))
    print_task_list("Still pending:", scheduler.filter_tasks(completed=False))
    print_task_list("Already completed:", scheduler.filter_tasks(completed=True))
    print_task_list(
        "Rex's pending tasks:",
        scheduler.filter_tasks(pet_name="Rex", completed=False),
    )

    # Recurring tasks: completing one auto-creates the next occurrence.
    print("\n" + "=" * 44)
    print("Recurring-task demo")
    print("=" * 44)
    walk = scheduler.find_task(1)  # Rex's daily "Morning walk"
    print(f"Completing: {walk.description} (due {walk.due_date}, {walk.frequency})")
    spawned = walk.mark_complete()
    print(
        f"  -> auto-created task #{spawned.task_id}: "
        f"{spawned.description} due {spawned.due_date} (still pending)"
    )
    print_task_list("Rex's tasks now:", scheduler.filter_tasks(pet_name="Rex"))

    # Conflict detection: flag tasks scheduled at the same time.
    print("\n" + "=" * 44)
    print("Conflict-detection demo")
    print("=" * 44)
    rex = {p.name: p for p in scheduler.all_pets()}["Rex"]
    # Cross-pet clash: Rex now also needs attention at 09:00 (Milo's meds).
    rex.add_task(CareTask(90, "Brush coat", "09:00", "daily", "grooming", priority=2))
    # Same-pet clash: Rex has a second task at 18:00 (his evening walk).
    rex.add_task(CareTask(91, "Give joint supplement", "18:00", "daily", "medication", priority=1))

    # Lightweight check: returns a warning string, never crashes.
    print(scheduler.check_conflicts())


if __name__ == "__main__":
    main()
