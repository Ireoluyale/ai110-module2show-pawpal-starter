"""PawPal+ core domain classes.

Full implementation of the PawPal+ domain model: tracking pet care tasks
across one or more pets and owners.

Design: containment (an object graph), matching the class responsibilities:
    Scheduler --> Owners --> Pets --> CareTasks
Each level holds the level beneath it, so a task is reached by navigating the
graph (owner.pets -> pet.tasks) rather than by joining on foreign-key ids.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CareTask:
    """A single pet-care activity."""

    task_id: int
    description: str
    time: str  # time of day as "HH:MM", e.g. "08:00"
    frequency: str  # how often, e.g. "daily", "weekly"
    category: str  # feeding, walk, medication, grooming
    priority: int  # 1 = highest priority; larger numbers are lower priority
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def mark_incomplete(self) -> None:
        """Reset this task to not done (e.g. for the next day)."""
        self.completed = False

    def summary(self) -> str:
        """Return a one-line human-readable summary of the task."""
        status = "done" if self.completed else "pending"
        return (
            f"[{status}] {self.time} {self.description} "
            f"({self.category}, p{self.priority}, {self.frequency})"
        )


@dataclass
class Pet:
    """A pet's profile plus the care tasks that belong to it."""

    pet_id: int
    name: str
    species: str
    breed: str
    age: int
    weight: float
    tasks: list[CareTask] = field(default_factory=list)

    def get_pet_info(self) -> str:
        """Return a summary of this pet's profile."""
        return (
            f"{self.name} ({self.species}, {self.breed}), "
            f"age {self.age}, {self.weight}kg"
        )

    def update_profile(self, **changes) -> None:
        """Update one or more profile attributes (name, species, breed, age, weight)."""
        allowed = {"name", "species", "breed", "age", "weight"}
        for key, value in changes.items():
            if key not in allowed:
                raise AttributeError(f"Cannot update unknown attribute: {key!r}")
            setattr(self, key, value)

    def add_task(self, task: CareTask) -> None:
        """Attach a care task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task_id: int) -> bool:
        """Remove a task by id. Returns True if one was removed."""
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        return len(self.tasks) < before

    def get_pending_tasks(self) -> list[CareTask]:
        """Return this pet's incomplete tasks, highest priority first."""
        return sorted(
            (t for t in self.tasks if not t.completed), key=lambda t: t.priority
        )


@dataclass
class Owner:
    """A pet owner who manages one or more pets."""

    owner_id: int
    name: str
    hours_available_daily: float
    reminders_enabled: bool
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet_id: int) -> bool:
        """Remove a pet by id. Returns True if one was removed."""
        before = len(self.pets)
        self.pets = [p for p in self.pets if p.pet_id != pet_id]
        return len(self.pets) < before

    def get_pet(self, pet_id: int) -> Optional[Pet]:
        """Return one of this owner's pets by id, or None if not found."""
        return next((p for p in self.pets if p.pet_id == pet_id), None)

    def get_all_tasks(self) -> list[CareTask]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]


@dataclass
class Scheduler:
    """The 'brain': retrieves, organizes, and manages tasks across pets.

    Holds a registry of owners and navigates Owner -> Pet -> CareTask to
    answer questions about tasks across the whole system.
    """

    owners: list[Owner] = field(default_factory=list)

    # --- registration -----------------------------------------------------
    def add_owner(self, owner: Owner) -> None:
        """Register an owner with the scheduler."""
        self.owners.append(owner)

    # --- traversal helpers -------------------------------------------------
    def all_pets(self) -> list[Pet]:
        """Return every pet across all owners."""
        return [pet for owner in self.owners for pet in owner.pets]

    def all_tasks(self) -> list[CareTask]:
        """Return every task across all pets of all owners."""
        return [task for pet in self.all_pets() for task in pet.tasks]

    # --- retrieval / organization -----------------------------------------
    def get_tasks_by_category(self, category: str) -> list[CareTask]:
        """Return all tasks in a given category, highest priority first."""
        return sorted(
            (t for t in self.all_tasks() if t.category == category),
            key=lambda t: t.priority,
        )

    def get_pending_tasks(self) -> list[CareTask]:
        """Return all incomplete tasks system-wide, highest priority first."""
        return sorted(
            (t for t in self.all_tasks() if not t.completed),
            key=lambda t: t.priority,
        )

    def get_tasks_by_priority(self) -> list[CareTask]:
        """Return every task ordered from highest to lowest priority."""
        return sorted(self.all_tasks(), key=lambda t: t.priority)

    def tasks_by_pet(self) -> dict[str, list[CareTask]]:
        """Group tasks under each pet's name, each list priority-sorted."""
        return {
            pet.name: sorted(pet.tasks, key=lambda t: t.priority)
            for pet in self.all_pets()
        }

    # --- management --------------------------------------------------------
    def find_task(self, task_id: int) -> Optional[CareTask]:
        """Locate a task anywhere in the system by id, or None."""
        return next((t for t in self.all_tasks() if t.task_id == task_id), None)

    def complete_task(self, task_id: int) -> bool:
        """Mark a task complete. Returns True if the task was found."""
        task = self.find_task(task_id)
        if task is None:
            return False
        task.mark_complete()
        return True
