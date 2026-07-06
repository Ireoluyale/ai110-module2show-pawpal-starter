"""Basic tests for the PawPal+ domain classes."""

import os
import sys

# Allow importing pawpal_system from the project root when tests run from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pawpal_system import Pet, CareTask


def make_task(task_id: int = 1) -> CareTask:
    return CareTask(
        task_id=task_id,
        description="Morning walk",
        time="08:00",
        frequency="daily",
        category="walk",
        priority=1,
    )


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
