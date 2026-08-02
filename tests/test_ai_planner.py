"""Tests for the AI care planner's deterministic rule-based fallback.

These tests never call the network: they exercise ``AIPlanner._fallback_plan``
(and ``plan_day`` with no API key), which is the safety net the app relies on
when Claude is unavailable. That keeps the suite reproducible in CI without an
ANTHROPIC_API_KEY.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_planner import AIPlanner, estimate_minutes
from pawpal_system import CareTask, Owner, Pet, Scheduler


def make_scheduler(hours: float, *tasks: CareTask) -> Scheduler:
    """One owner, one pet, the given tasks — with a chosen daily time budget."""
    pet = Pet(pet_id=1, name="Rex", species="dog", breed="Lab", age=3, weight=30.0)
    for t in tasks:
        pet.add_task(t)
    owner = Owner(owner_id=1, name="Ada", hours_available_daily=hours, reminders_enabled=True)
    owner.add_pet(pet)
    scheduler = Scheduler()
    scheduler.add_owner(owner)
    return scheduler


def task(task_id, time, category, priority):
    return CareTask(
        task_id=task_id,
        description=f"task-{task_id}",
        time=time,
        frequency="daily",
        category=category,
        priority=priority,
    )


def test_fallback_used_without_api_key(monkeypatch):
    """With no ANTHROPIC_API_KEY, plan_day must use the rule-based fallback."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    scheduler = make_scheduler(2.0, task(1, "08:00", "walk", 1))
    result = AIPlanner(scheduler).plan_day()

    assert result.used_ai is False
    assert "rule-based" in result.note.lower()
    assert [t.task_id for t in result.ordered] == [1]


def test_over_budget_tasks_are_deferred(monkeypatch):
    """When tasks exceed the time budget, the lowest-priority ones are deferred."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # Budget = 0.5h = 30 min. Two 30-min walks can't both fit.
    scheduler = make_scheduler(
        0.5,
        task(1, "08:00", "walk", 1),   # high priority, 30 min
        task(2, "12:00", "walk", 3),   # low priority, 30 min
    )
    result = AIPlanner(scheduler).plan_day()

    assert [t.task_id for t in result.ordered] == [1]     # high priority kept
    assert [t.task_id for t in result.deferred] == [2]    # low priority deferred
    assert result.total_minutes <= 30


def test_same_time_conflict_keeps_higher_priority(monkeypatch):
    """Two tasks at the same time: keep the higher priority, defer the other."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    scheduler = make_scheduler(
        4.0,
        task(1, "09:00", "medication", 2),  # same slot, lower priority
        task(2, "09:00", "feeding", 1),     # same slot, higher priority -> kept
    )
    result = AIPlanner(scheduler).plan_day()

    ordered_ids = {t.task_id for t in result.ordered}
    deferred_ids = {t.task_id for t in result.deferred}
    assert ordered_ids == {2}
    assert deferred_ids == {1}


def test_empty_schedule_returns_no_plan(monkeypatch):
    """No pending tasks -> an empty plan with an explanatory reason, no crash."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    scheduler = make_scheduler(2.0)
    result = AIPlanner(scheduler).plan_day()

    assert result.ordered == []
    assert result.deferred == []
    assert "nothing pending" in result.reasoning.lower()


def test_estimate_minutes_by_category():
    """Duration estimates are category-driven with a sensible default."""
    assert estimate_minutes(task(1, "08:00", "walk", 1)) == 30
    assert estimate_minutes(task(2, "08:00", "medication", 1)) == 5
    assert estimate_minutes(task(3, "08:00", "unknown-category", 1)) == 15
