# PawPal+ System Diagram

How the pieces fit together and how a request flows from input to a validated
plan. The AI feature is an **agentic workflow**: the agent plans, acts on the
live `Scheduler` through tools, and checks its own work with a validator before
submitting. Human review and the automated test suite are the two places where
AI results are checked.

```mermaid
flowchart TD
    %% ---------- INPUT ----------
    User(["👤 User"])
    subgraph INPUT["Input"]
        UI["Streamlit UI (app.py)<br/>add pets / tasks,<br/>click 'Generate AI plan'"]
        CLI["CLI demo (main.py, ai_planner.py)"]
    end
    User -->|enters pets, tasks, budget| UI
    User -->|runs demo| CLI

    %% ---------- DOMAIN STATE ----------
    subgraph DOMAIN["Domain model (pawpal_system.py)"]
        Scheduler["Scheduler — the 'brain'<br/>Owner → Pet → CareTask"]
    end
    UI -->|build state| Scheduler
    CLI -->|build state| Scheduler

    %% ---------- AGENT / PROCESS ----------
    subgraph AGENT["Agentic AI Planner (ai_planner.py)"]
        Plan["AIPlanner.plan_day()<br/>PLAN the day"]
        subgraph TOOLS["Tools — agent ACTS on live data"]
            Inspect["inspect_schedule()"]
            Conflicts["check_conflicts()"]
            Validate{{"validate_plan()<br/>SELF-CHECK:<br/>budget + conflicts<br/>PASS / FAIL"}}
        end
        Submit["submit_plan()<br/>final validated plan"]
        Fallback["_fallback_plan()<br/>deterministic rule-based<br/>(guardrail)"]
    end

    Claude["🤖 Claude API<br/>(claude-opus-5)"]

    UI -->|click| Plan
    CLI --> Plan
    Plan <-->|tool-use loop| Claude
    Plan --> Inspect
    Plan --> Conflicts
    Inspect -->|reads| Scheduler
    Conflicts -->|reads| Scheduler
    Validate -->|re-runs real conflict<br/>+ budget logic| Scheduler

    %% agent checks its own work, then revises or submits
    Plan --> Validate
    Validate -->|FAIL — revise| Plan
    Validate -->|PASS| Submit

    %% guardrail: no API key or API error
    Plan -. "no API key /<br/>API error" .-> Fallback

    %% ---------- OUTPUT ----------
    subgraph OUTPUT["Output"]
        Result["PlanResult<br/>ordered + deferred tasks,<br/>reasoning, AI/rule badge"]
        Log["pawpal_ai.log<br/>(every tool call logged)"]
    end
    Submit --> Result
    Fallback --> Result
    Plan -.logs.-> Log
    Result -->|displayed| UI
    Result -->|printed| CLI

    %% ---------- HUMAN + TESTING CHECKS ----------
    Review["✅ Human review<br/>user reads plan + reasoning<br/>in the UI"]
    Tests["🧪 pytest suite<br/>(tests/test_ai_planner.py)<br/>checks fallback logic:<br/>budget, conflicts, empty case"]

    Result --> Review
    Fallback -.verified by.-> Tests
    Validate -.mirrored by.-> Tests

    %% ---------- styling ----------
    classDef check fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20;
    classDef ai fill:#ede7f6,stroke:#5e35b1,color:#311b92;
    class Validate,Review,Tests check;
    class Claude,Plan ai;
```

## Where AI results get checked

| Checkpoint | What it checks | Where in code |
|---|---|---|
| **`validate_plan` (self-check)** | The agent checks its **own** proposed plan against the real conflict + time-budget logic and must get `PASS` before submitting. | `ai_planner.py` → `validate_plan` |
| **Human review** | The user reads the final ordered plan and the AI's written reasoning in the UI and decides whether to act on it. | `app.py` → AI Care Planner section |
| **Automated tests** | `pytest` verifies the deterministic fallback (budget limits, conflict resolution, empty schedule) — the same rules the AI's validator enforces. | `tests/test_ai_planner.py` |

## Data flow in one line

**Input** (pets/tasks/budget) → **Scheduler** state → **Agent** plans and calls
tools → **self-check** (`validate_plan`) loops until PASS → **submit** (or
**fallback** if no key) → **PlanResult** → shown to the **user** for review.
