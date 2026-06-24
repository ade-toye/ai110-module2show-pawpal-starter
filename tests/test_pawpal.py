from pawpal_system import Task, Pet, Priority


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
