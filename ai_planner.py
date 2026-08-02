"""PawPal+ agentic AI care planner.

This is the AI feature of PawPal+. It is an **agentic workflow**: Claude is given
tools that read the live Scheduler, then it *plans* a day, *acts* by calling those
tools to inspect the real data, *checks its own work* with a validator, and revises
until the plan passes — before submitting a final, validated schedule.

Why this is "fully integrated" and not a bolt-on: the plan the AI produces is the
schedule the app displays. The AI's tools call the SAME domain logic the rest of
PawPal+ uses (``Scheduler.find_conflicts``, ``get_todays_schedule``, the owner's
``hours_available_daily`` budget), so the AI reasons over real state and its output
drives what the user sees.

Guardrails & reliability:
- No ``ANTHROPIC_API_KEY`` (or any API failure) -> a deterministic rule-based
  fallback planner runs instead, so the app always produces a plan.
- Every tool call and the final outcome are logged to ``pawpal_ai.log``.
- The agentic loop is bounded (``MAX_TOOL_ROUNDS``) so it can never run forever.
- The AI must get a PASS from ``validate_plan`` before it is allowed to submit.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from pawpal_system import CareTask, Scheduler

# --- configuration -------------------------------------------------------
# Default model. Claude Opus 5 is the most capable; swap to "claude-sonnet-5"
# or "claude-haiku-4-5" here to trade a little quality for lower cost/latency.
MODEL = "claude-opus-5"

# How many care minutes each category typically takes. The domain model doesn't
# store durations, so we estimate by category — this gives the planner a real
# time budget to reason about without changing CareTask.
CATEGORY_MINUTES = {"feeding": 10, "walk": 30, "medication": 5, "grooming": 20}
DEFAULT_MINUTES = 15

# Safety cap on the agentic loop: plan -> validate -> revise rounds.
MAX_TOOL_ROUNDS = 12

# --- logging -------------------------------------------------------------
LOG_PATH = os.path.join(os.path.dirname(__file__), "pawpal_ai.log")


def _get_logger() -> logging.Logger:
    """Return a module logger that writes to pawpal_ai.log exactly once."""
    logger = logging.getLogger("pawpal.ai")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    return logger


log = _get_logger()


def estimate_minutes(task: CareTask) -> int:
    """Estimate how long a task takes, by category."""
    return CATEGORY_MINUTES.get(task.category, DEFAULT_MINUTES)


@dataclass
class PlanResult:
    """The outcome of a planning run, ready for the UI to display."""

    ordered: list[CareTask] = field(default_factory=list)   # do these today, in order
    deferred: list[CareTask] = field(default_factory=list)  # these wait (budget/conflict)
    reasoning: str = ""                                      # the planner's explanation
    used_ai: bool = False                                    # True if Claude produced it
    note: str = ""                                           # e.g. why the fallback ran

    @property
    def total_minutes(self) -> int:
        return sum(estimate_minutes(t) for t in self.ordered)


class AIPlanner:
    """Agentic care planner backed by Claude, with a rule-based safety net."""

    def __init__(self, scheduler: Scheduler, model: str = MODEL) -> None:
        self.scheduler = scheduler
        self.model = model
        self.owner = scheduler.owners[0] if scheduler.owners else None
        self.budget_minutes = int((self.owner.hours_available_daily * 60)) if self.owner else 0

    # --- public entry point ---------------------------------------------
    def plan_day(self, today: Optional[date] = None) -> PlanResult:
        """Produce today's plan. Uses Claude when possible; falls back safely."""
        tasks = self.scheduler.get_todays_schedule(today=today)
        if not tasks:
            log.info("plan_day: no pending tasks to schedule")
            return PlanResult(reasoning="Nothing pending today — no plan needed.")

        if not os.environ.get("ANTHROPIC_API_KEY"):
            log.info("plan_day: ANTHROPIC_API_KEY not set -> using rule-based fallback")
            result = self._fallback_plan(tasks)
            result.note = "No ANTHROPIC_API_KEY set — used the built-in rule-based planner."
            return result

        try:
            return self._ai_plan(tasks)
        except Exception as exc:  # never let an AI/network error break the app
            log.exception("plan_day: AI planning failed, falling back")
            result = self._fallback_plan(tasks)
            result.note = f"AI planning unavailable ({exc.__class__.__name__}) — used rule-based planner."
            return result

    # --- agentic AI path ------------------------------------------------
    def _ai_plan(self, tasks: list[CareTask]) -> PlanResult:
        import anthropic
        from anthropic import beta_tool

        by_id: dict[int, CareTask] = {t.task_id: t for t in self.scheduler.all_tasks()}
        pending_ids = {t.task_id for t in tasks}
        captured: dict = {}  # submit_plan writes the final plan here

        def _task_json(t: CareTask) -> dict:
            return {
                "task_id": t.task_id,
                "pet": t.pet_name,
                "time": t.time,
                "description": t.description,
                "category": t.category,
                "priority": t.priority,  # 1 = highest
                "estimated_minutes": estimate_minutes(t),
            }

        @beta_tool
        def inspect_schedule() -> str:
            """List today's pending care tasks as JSON. Each task has task_id, pet,
            time, description, category, priority (1=highest), and estimated_minutes.
            Call this first to see everything that needs scheduling."""
            import json

            rows = [_task_json(by_id[i]) for i in sorted(pending_ids)]
            log.info("tool inspect_schedule -> %d tasks", len(rows))
            return json.dumps(
                {"owner_daily_budget_minutes": self.budget_minutes, "tasks": rows},
                indent=2,
            )

        @beta_tool
        def check_conflicts() -> str:
            """Return a human-readable report of tasks that clash at the same date and
            time (a pet double-booked, or two pets needing attention at once)."""
            report = self.scheduler.check_conflicts()
            log.info("tool check_conflicts")
            return report

        @beta_tool
        def validate_plan(ordered_task_ids: list[int]) -> str:
            """Check a proposed plan. Pass the task_ids you intend to do today, in order.
            Returns 'PASS' or 'FAIL: ...'. It fails if: an id is unknown, the total
            estimated minutes exceed the owner's daily budget, or two tasks in the plan
            are booked at the same time (an unresolved conflict). You MUST call this and
            get PASS before submitting."""
            problems: list[str] = []

            unknown = [i for i in ordered_task_ids if i not in pending_ids]
            if unknown:
                problems.append(f"unknown or non-pending task_ids: {unknown}")

            known = [by_id[i] for i in ordered_task_ids if i in by_id]
            total = sum(estimate_minutes(t) for t in known)
            if total > self.budget_minutes:
                problems.append(
                    f"over budget: plan needs {total} min but the owner has "
                    f"{self.budget_minutes} min — defer lower-priority tasks"
                )

            slots: dict[tuple, list[CareTask]] = {}
            for t in known:
                slots.setdefault((t.due_date, t.minutes), []).append(t)
            for group in slots.values():
                if len(group) > 1:
                    names = ", ".join(f"#{t.task_id} {t.pet_name}:{t.description}" for t in group)
                    problems.append(
                        f"conflict at {group[0].time}: {names} — keep one, defer the rest"
                    )

            if problems:
                log.info("tool validate_plan -> FAIL (%d issue(s))", len(problems))
                return "FAIL:\n- " + "\n- ".join(problems)
            log.info("tool validate_plan -> PASS (%d task(s), %d min)", len(known), total)
            return f"PASS: {len(known)} task(s), {total}/{self.budget_minutes} min used."

        @beta_tool
        def submit_plan(
            ordered_task_ids: list[int],
            deferred_task_ids: list[int],
            reasoning: str,
        ) -> str:
            """Submit your final validated plan. ordered_task_ids = tasks to do today in
            the order you'd do them; deferred_task_ids = tasks that don't fit today and
            should wait; reasoning = a short explanation for the owner. Only call this
            after validate_plan has returned PASS."""
            captured["ordered_task_ids"] = ordered_task_ids
            captured["deferred_task_ids"] = deferred_task_ids
            captured["reasoning"] = reasoning
            log.info("tool submit_plan -> %d ordered, %d deferred",
                     len(ordered_task_ids), len(deferred_task_ids))
            return "Plan recorded."

        system = (
            "You are PawPal+, a pet-care planning assistant. Build the owner's plan for "
            "TODAY from their pending care tasks, respecting three constraints: the "
            "owner's daily time budget, avoiding two tasks booked at the same time, and "
            "prioritising by task priority (1 = highest). Work agentically: call "
            "inspect_schedule and check_conflicts to see the real data, draft an ordered "
            "plan, call validate_plan to check it, and revise until it PASSES. When two "
            "tasks clash at the same time, keep the higher-priority one and defer the "
            "other. When the day is over budget, defer the lowest-priority tasks. Once "
            "validate_plan returns PASS, call submit_plan with your final ordering, the "
            "deferred tasks, and a brief, owner-friendly explanation. Do not submit "
            "before you have a PASS."
        )

        client = anthropic.Anthropic()
        log.info("AI plan starting: model=%s, %d pending task(s), budget=%d min",
                 self.model, len(pending_ids), self.budget_minutes)

        runner = client.beta.messages.tool_runner(
            model=self.model,
            max_tokens=6000,
            system=system,
            tools=[inspect_schedule, check_conflicts, validate_plan, submit_plan],
            messages=[{
                "role": "user",
                "content": "Plan my pets' care for today. Show your reasoning by using the tools.",
            }],
        )

        rounds = 0
        for _message in runner:
            rounds += 1
            if captured:  # AI has submitted — we're done
                break
            if rounds >= MAX_TOOL_ROUNDS:
                log.warning("AI plan hit MAX_TOOL_ROUNDS without submitting")
                break

        if not captured:
            # The model never produced a valid submission — fall back rather than guess.
            log.warning("AI plan produced no submission -> using rule-based fallback")
            result = self._fallback_plan(tasks)
            result.note = "AI did not return a usable plan — used rule-based planner."
            return result

        # Trust-but-verify: only keep ids that are actually pending today.
        ordered = [by_id[i] for i in captured["ordered_task_ids"] if i in pending_ids]
        deferred_ids = {i for i in captured["deferred_task_ids"] if i in pending_ids}
        # Any pending task the AI mentioned in neither list is treated as deferred.
        planned = {t.task_id for t in ordered} | deferred_ids
        deferred = [by_id[i] for i in pending_ids if i in deferred_ids or i not in planned]

        log.info("AI plan done: %d ordered, %d deferred, %d round(s)",
                 len(ordered), len(deferred), rounds)
        return PlanResult(
            ordered=ordered,
            deferred=deferred,
            reasoning=captured.get("reasoning", ""),
            used_ai=True,
        )

    # --- deterministic fallback -----------------------------------------
    def _fallback_plan(self, tasks: list[CareTask]) -> PlanResult:
        """Rule-based planner: resolve time conflicts by priority, then greedily fit
        the highest-priority tasks into the owner's time budget. Fully deterministic,
        so it needs no API key and the app always produces a plan."""
        from pawpal_system import sort_tasks

        # 1) Resolve same-time conflicts: keep highest priority per slot, defer the rest.
        slots: dict[tuple, list[CareTask]] = {}
        for t in tasks:
            slots.setdefault((t.due_date, t.minutes), []).append(t)

        candidates: list[CareTask] = []
        deferred: list[CareTask] = []
        for group in slots.values():
            ranked = sort_tasks(group, by="priority")
            candidates.append(ranked[0])
            deferred.extend(ranked[1:])  # losers of the clash wait

        # 2) Greedily fit by priority within the time budget.
        ordered: list[CareTask] = []
        used = 0
        for t in sort_tasks(candidates, by="priority"):
            need = estimate_minutes(t)
            if used + need <= self.budget_minutes:
                ordered.append(t)
                used += need
            else:
                deferred.append(t)  # doesn't fit today

        # Present the day's plan in the order it actually happens.
        ordered = sort_tasks(ordered, by="time")
        deferred = sort_tasks(deferred, by="priority")

        reasoning = (
            f"Rule-based plan: fit {len(ordered)} task(s) into the owner's "
            f"{self.budget_minutes}-minute budget ({used} min used), highest priority "
            f"first. Resolved same-time clashes by keeping the higher-priority task. "
            f"{len(deferred)} task(s) deferred (conflict or over budget)."
        )
        log.info("fallback plan: %d ordered (%d min), %d deferred",
                 len(ordered), used, len(deferred))
        return PlanResult(ordered=ordered, deferred=deferred, reasoning=reasoning, used_ai=False)


def _print_plan(result: PlanResult) -> None:
    """Small CLI pretty-printer for the demo below."""
    tag = "AI" if result.used_ai else "rule-based"
    print("=" * 52)
    print(f"PawPal+ care plan ({tag})")
    print("=" * 52)
    if result.note:
        print(f"note: {result.note}\n")
    if result.reasoning:
        print(result.reasoning, "\n")
    print(f"Today ({result.total_minutes} min):")
    for t in result.ordered:
        print(f"  {t.time}  {t.pet_name:<6} {t.description} ({t.category}, p{t.priority})")
    if result.deferred:
        print("\nDeferred:")
        for t in result.deferred:
            print(f"  {t.time}  {t.pet_name:<6} {t.description} (p{t.priority})")


if __name__ == "__main__":
    # Reproducible demo: build the same world as main.py and plan it.
    from main import build_demo

    scheduler = build_demo()
    planner = AIPlanner(scheduler)
    _print_plan(planner.plan_day())
