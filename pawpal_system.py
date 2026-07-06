"""PawPal+ core domain classes.

Full implementation of the PawPal+ domain model: tracking pet care tasks
across one or more pets and owners.

Design: containment (an object graph), matching the class responsibilities:
    Scheduler --> Owners --> Pets --> CareTasks
Each level holds the level beneath it, so a task is reached by navigating the
graph (owner.pets -> pet.tasks) rather than by joining on foreign-key ids.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import ClassVar, Optional


# How far ahead the next occurrence of a recurring task falls. A task whose
# frequency isn't in here (e.g. "once") simply doesn't recur.
_FREQUENCY_DELTAS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


def _parse_hhmm(value: str) -> int:
    """Convert a 'HH:MM' 24-hour time string into minutes since midnight.

    Raises ValueError if the string is not a valid time. This is what makes
    time comparisons reliable instead of depending on lexicographic string
    order (where '9:00' would wrongly sort after '18:00').
    """
    try:
        hours, minutes = value.split(":")
        h, m = int(hours), int(minutes)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid time {value!r}; expected 'HH:MM'") from None
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"Time out of range {value!r}; expected 00:00-23:59")
    return h * 60 + m


def sort_tasks(tasks: list["CareTask"], by: str = "time") -> list["CareTask"]:
    """Return tasks sorted by a reusable composite key.

    "time"     -> earliest first, ties broken by priority (highest first)
    "priority" -> highest priority first, ties broken by earliest time

    This replaces the single-key ``sorted(..., key=...)`` calls that were
    duplicated across the codebase, and gives sensible tie-breaking for free.
    """
    keyers = {
        "time": lambda t: (t.minutes, t.priority),
        "priority": lambda t: (t.priority, t.minutes),
    }
    if by not in keyers:
        raise ValueError(f"Unknown sort key {by!r}; expected one of {list(keyers)}")
    return sorted(tasks, key=keyers[by])


@dataclass
class CareTask:
    """A single pet-care activity."""

    # Tracks the largest task_id seen so auto-generated occurrences get a
    # fresh, unique id without colliding with manually assigned ones.
    _id_counter: ClassVar[int] = 0

    task_id: int
    description: str
    time: str  # time of day as "HH:MM", e.g. "08:00"
    frequency: str  # how often, e.g. "daily", "weekly"
    category: str  # feeding, walk, medication, grooming
    priority: int  # 1 = highest priority; larger numbers are lower priority
    completed: bool = False
    due_date: date = field(default_factory=date.today)
    # Back-reference to the owning pet, set by Pet.add_task. Excluded from repr
    # and equality so the Pet <-> CareTask cycle doesn't recurse infinitely.
    pet: Optional["Pet"] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        # Validate the time up front so bad data fails loudly at creation,
        # not later during a sort.
        _parse_hhmm(self.time)
        # Keep the id counter ahead of every id we've ever seen.
        CareTask._id_counter = max(CareTask._id_counter, self.task_id)

    @property
    def minutes(self) -> int:
        """This task's time as minutes since midnight, for correct ordering."""
        return _parse_hhmm(self.time)

    def is_recurring(self) -> bool:
        """True if this task repeats on a known schedule (daily/weekly)."""
        return self.frequency in _FREQUENCY_DELTAS

    def next_occurrence(self) -> "CareTask":
        """Build the next dated, incomplete copy of this recurring task.

        The new task keeps every attribute except: a fresh unique id, a
        due_date advanced by the frequency, and completed reset to False.
        Raises ValueError if the task doesn't recur.
        """
        if not self.is_recurring():
            raise ValueError(f"Task {self.task_id} ({self.frequency!r}) does not recur")
        return CareTask(
            task_id=CareTask._id_counter + 1,
            description=self.description,
            time=self.time,
            frequency=self.frequency,
            category=self.category,
            priority=self.priority,
            completed=False,
            due_date=self.due_date + _FREQUENCY_DELTAS[self.frequency],
        )

    @property
    def pet_name(self) -> str:
        """Name of the owning pet, or '?' if this task isn't attached to one."""
        return self.pet.name if self.pet is not None else "?"

    def mark_complete(self) -> Optional["CareTask"]:
        """Mark this task as done and roll a recurring task to its next date.

        If this is a recurring task attached to a pet, a fresh incomplete copy
        for the next occurrence is created and added to that pet automatically;
        the new task is returned. Returns None when nothing was spawned (task
        is one-off, already done, or not attached to a pet).
        """
        if self.completed:
            return None
        self.completed = True
        if self.is_recurring() and self.pet is not None:
            next_task = self.next_occurrence()
            self.pet.add_task(next_task)
            return next_task
        return None

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
        """Attach a care task to this pet, recording the back-reference."""
        task.pet = self
        self.tasks.append(task)

    def remove_task(self, task_id: int) -> bool:
        """Remove a task by id. Returns True if one was removed."""
        before = len(self.tasks)
        removed = [t for t in self.tasks if t.task_id == task_id]
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        for t in removed:
            t.pet = None
        return len(self.tasks) < before

    def get_pending_tasks(self) -> list[CareTask]:
        """Return this pet's incomplete tasks, highest priority first."""
        return sort_tasks([t for t in self.tasks if not t.completed], by="priority")


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
        return sort_tasks(
            [t for t in self.all_tasks() if t.category == category], by="priority"
        )

    def get_pending_tasks(self) -> list[CareTask]:
        """Return all incomplete tasks system-wide, highest priority first."""
        return sort_tasks(
            [t for t in self.all_tasks() if not t.completed], by="priority"
        )

    def get_todays_schedule(self, today: Optional[date] = None) -> list[CareTask]:
        """Return pending tasks due on or before `today`, ordered by time.

        Filtering by due_date keeps tomorrow's freshly spawned recurring
        occurrences out of today's list. `today` defaults to the real date.
        """
        today = today or date.today()
        return sort_tasks(
            [t for t in self.all_tasks() if not t.completed and t.due_date <= today],
            by="time",
        )

    def sort_by_time(self) -> list[CareTask]:
        """Return every task ordered by time of day, earliest first.

        The classic way to do this is a lambda key passed to sorted():

            sorted(self.all_tasks(), key=lambda t: t.time)

        That lambda runs once per task and returns the value to sort on.
        Sorting the raw "HH:MM" string works ONLY because the format is
        zero-padded 24-hour text ("08:00" < "18:00"). It would break on
        "9:00", so we sort on the parsed numeric minutes instead:
        """
        return sorted(self.all_tasks(), key=lambda t: t.minutes)

    def filter_tasks(
        self,
        *,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> list[CareTask]:
        """Return tasks matching the given criteria, ordered by time.

        Both filters are optional and combine (AND). Passing neither returns
        every task; passing one applies just that one:

            filter_tasks(pet_name="Milo")            # all of Milo's tasks
            filter_tasks(completed=False)            # everything still pending
            filter_tasks(pet_name="Rex", completed=True)  # Rex's done tasks

        Keyword-only args keep call sites self-documenting, and using None as
        the default lets us distinguish "don't filter" from completed=False.
        """
        tasks = self.all_tasks()
        if pet_name is not None:
            tasks = [t for t in tasks if t.pet_name == pet_name]
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        return sort_tasks(tasks, by="time")

    def find_conflicts(self, *, pending_only: bool = True) -> list[list[CareTask]]:
        """Find tasks that clash on the same date and time of day.

        Groups tasks by (due_date, time) and returns every group holding more
        than one task. Because the grouping ignores which pet a task belongs
        to, it catches both kinds of clash:
          - same pet double-booked (e.g. two of Rex's tasks at 18:00)
          - different pets needing attention at once (Rex + Milo both at 08:00)

        Completed tasks are ignored by default since they no longer compete
        for the owner's time. Groups are ordered earliest-first; within a
        group, highest-priority tasks come first.
        """
        tasks = self.all_tasks()
        if pending_only:
            tasks = [t for t in tasks if not t.completed]

        by_slot: dict[tuple[date, int], list[CareTask]] = {}
        for task in tasks:
            by_slot.setdefault((task.due_date, task.minutes), []).append(task)

        conflicts = [sort_tasks(group, by="priority") for group in by_slot.values() if len(group) > 1]
        conflicts.sort(key=lambda group: (group[0].due_date, group[0].minutes))
        return conflicts

    def check_conflicts(self) -> str:
        """Lightweight conflict check: return a human-readable warning string.

        Unlike find_conflicts (which returns structured task groups), this is
        meant for quick display. It never raises — any unexpected error is
        swallowed into a warning line, so calling it can't crash the program.
        Returns a friendly all-clear message when there are no conflicts.
        """
        try:
            conflicts = self.find_conflicts()
        except Exception as exc:  # stay safe: report, don't crash
            return f"[!] Could not check for conflicts: {exc}"

        if not conflicts:
            return "[OK] No scheduling conflicts."

        lines = [f"[!] {len(conflicts)} scheduling conflict(s) found:"]
        for group in conflicts:
            pets = {t.pet_name for t in group}
            kind = "same pet" if len(pets) == 1 else "different pets"
            names = ", ".join(f"{t.pet_name}: {t.description}" for t in group)
            lines.append(f"  - {group[0].time} ({kind}) -> {names}")
        return "\n".join(lines)

    def get_tasks_by_priority(self) -> list[CareTask]:
        """Return every task ordered from highest to lowest priority."""
        return sort_tasks(self.all_tasks(), by="priority")

    def tasks_by_pet(self) -> dict[str, list[CareTask]]:
        """Group tasks under each pet's name, each list priority-sorted."""
        return {
            pet.name: sort_tasks(pet.tasks, by="priority")
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
