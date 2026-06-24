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

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Sort by time | `DailyPlanner.sort_by_time()` | Sorts tasks by `pinned_start_time` ascending; unpinned tasks fall to the end via a `float("inf")` sentinel key |
| Sort by priority | `DailyPlanner.sort_by_priority()` | Orders tasks HIGH → MEDIUM → LOW so the most important care happens first when filling free slots |
| Filter by pet or status | `DailyPlanner.filter_tasks()` | Returns tasks matching an optional pet name, completion status, or both combined (AND logic) |
| Conflict detection | `DailyPlanner._detect_conflicts()` | Groups scheduled tasks by pet and checks adjacent pairs for time overlap in O(n); issues a `UserWarning` instead of crashing so the rest of the plan still displays |
| Recurring task scheduling | `Task.next_occurrence()` + `DailyPlanner.complete_task()` | When a recurring task is marked complete, `complete_task()` calls `next_occurrence()` to clone the task with `completed=False` and a new `due_date` — +1 day for daily, +7 days for weekly — and adds it back to the pet's task list automatically |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

## Sample Output
Daily plan for Toye — 2026-06-24:
  17:00 — Walk Bugsy (30 min) [high]
  19:00 — Feed Bugsy (15 min) [high]
  21:00 — Bathe Pero (20 min) [high]

