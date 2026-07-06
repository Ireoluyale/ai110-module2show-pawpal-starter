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

    rex.add_task(CareTask(1, "Morning walk", "08:00", "daily", "walk", priority=2))
    rex.add_task(CareTask(2, "Evening walk", "18:00", "daily", "walk", priority=2))
    milo.add_task(CareTask(3, "Give allergy meds", "09:00", "daily", "medication", priority=1))
    milo.add_task(CareTask(4, "Refill food bowl", "07:30", "daily", "feeding", priority=1))

    owner.add_pet(rex)
    owner.add_pet(milo)

    scheduler = Scheduler()
    scheduler.add_owner(owner)
    return scheduler


def print_todays_schedule(scheduler: Scheduler) -> None:
    """Print all pending tasks across pets, ordered by time of day."""
    pet_by_task = {
        task.task_id: pet.name
        for pet in scheduler.all_pets()
        for task in pet.tasks
    }

    pending = scheduler.get_pending_tasks()
    schedule = sorted(pending, key=lambda t: t.time)

    print("=" * 44)
    print("Today's Schedule")
    print("=" * 44)

    if not schedule:
        print("Nothing left to do today. \U0001F415")
        return

    for task in schedule:
        pet_name = pet_by_task.get(task.task_id, "?")
        print(f"{task.time}  {pet_name:<5}  {task.description} ({task.category})")

    print("-" * 44)
    print(f"{len(schedule)} task(s) remaining today.")


def main() -> None:
    scheduler = build_demo()
    print_todays_schedule(scheduler)


if __name__ == "__main__":
    main()
