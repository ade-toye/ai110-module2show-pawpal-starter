import warnings
from pawpal_system import (
    Task, Pet, Owner, Priority, Constraint, DailyPlanner, ScheduledTask
)


def test_mark_complete_changes_task_status():
    task = Task(name="Walk", category="exercise", duration_minutes=30, priority=Priority.HIGH)
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Bugsy", species="dog", breed="Mixed", age=3)
    task = Task(name="Walk", category="exercise", duration_minutes=30, priority=Priority.HIGH)
    before = len(pet.tasks)
    pet.add_task(task)
    assert len(pet.tasks) == before + 1


# --- Sorting correctness ---

def test_generate_plan_returns_tasks_in_chronological_order():
    """Scheduled tasks must come back sorted by start_time ascending."""
    pet = Pet(name="Rex", species="dog", breed="Lab", age=2)
    pet.add_task(Task(name="Evening walk", category="exercise", duration_minutes=20, priority=Priority.LOW))
    pet.add_task(Task(name="Feeding", category="feeding", duration_minutes=10, priority=Priority.HIGH))
    pet.add_task(Task(name="Grooming", category="grooming", duration_minutes=15, priority=Priority.MEDIUM))

    owner = Owner(name="Alice")
    owner.add_pet(pet)
    constraints = Constraint(start_time="08:00", end_time="18:00")
    planner = DailyPlanner(date="2026-06-25", owner=owner, constraints=constraints)

    plan = planner.generate_plan()

    start_times = [planner._to_minutes(st.start_time) for st in plan]
    assert start_times == sorted(start_times), "Scheduled tasks are not in chronological order"


# --- Recurrence logic ---

def test_complete_daily_task_queues_next_occurrence():
    """Completing a daily recurring task adds a new task due the following day."""
    pet = Pet(name="Mochi", species="cat", breed="Siamese", age=4)
    task = Task(
        name="Morning feed",
        category="feeding",
        duration_minutes=10,
        priority=Priority.HIGH,
        recurring=True,
        frequency="daily",
    )
    pet.add_task(task)

    owner = Owner(name="Bob")
    owner.add_pet(pet)
    constraints = Constraint(start_time="07:00", end_time="20:00")
    planner = DailyPlanner(date="2026-06-25", owner=owner, constraints=constraints)

    next_task = planner.complete_task(pet, task)

    assert task.completed is True, "Original task should be marked complete"
    assert next_task is not None, "A follow-up task should be created for a daily recurring task"
    assert next_task.due_date == "2026-06-26", f"Expected next occurrence on 2026-06-26, got {next_task.due_date}"
    assert next_task.completed is False, "Next occurrence should start as incomplete"
    assert next_task in pet.tasks, "Next occurrence should be added to the pet's task list"


# --- Conflict detection ---

def test_detect_conflicts_warns_on_same_start_time():
    """Two tasks pinned to the same start time for the same pet should trigger a UserWarning."""
    pet = Pet(name="Noodle", species="dog", breed="Poodle", age=1)
    pet.add_task(Task(
        name="Walk",
        category="exercise",
        duration_minutes=30,
        priority=Priority.HIGH,
        pinned_start_time="09:00",
    ))
    pet.add_task(Task(
        name="Training",
        category="training",
        duration_minutes=20,
        priority=Priority.MEDIUM,
        pinned_start_time="09:00",
    ))

    owner = Owner(name="Carol")
    owner.add_pet(pet)
    constraints = Constraint(start_time="08:00", end_time="18:00")
    planner = DailyPlanner(date="2026-06-25", owner=owner, constraints=constraints)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        planner.generate_plan()

    conflict_warnings = [w for w in caught if "conflict" in str(w.message).lower()]
    assert conflict_warnings, "Expected a scheduling conflict warning for overlapping pinned tasks"
