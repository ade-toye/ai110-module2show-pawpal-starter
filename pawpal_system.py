from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import anthropic
import json
import warnings


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Task:
    name: str
    category: str
    duration_minutes: int
    priority: Priority
    recurring: bool = False
    frequency: Optional[str] = None  # "daily" or "weekly" — only set when recurring=True
    completed: bool = False
    pinned_start_time: Optional[str] = None  # "HH:MM" — locks this task to an exact start time
    due_date: Optional[str] = None  # "YYYY-MM-DD" — set automatically on recurring task completion

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def mark_incomplete(self) -> None:
        """Reset this task to not done."""
        self.completed = False

    def next_occurrence(self, from_date: str) -> "Task":
        """Return a fresh, incomplete copy of this task scheduled for its next occurrence.

        Calculates the next due date by adding 1 day (daily) or 7 days (weekly)
        to from_date using timedelta. All other fields are preserved unchanged.

        Args:
            from_date: The current plan date in "YYYY-MM-DD" format.

        Returns:
            A new Task with completed=False and due_date set to the next occurrence date.
        """
        current = datetime.strptime(from_date, "%Y-%m-%d").date()
        if self.frequency == "daily":
            next_date = current + timedelta(days=1)
        elif self.frequency == "weekly":
            next_date = current + timedelta(weeks=1)
        else:
            next_date = current
        return replace(self, completed=False, due_date=next_date.strftime("%Y-%m-%d"))


@dataclass
class ScheduledTask:
    task: Task
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    pet_name: str = ""

    def get_summary(self) -> str:
        """Return a single-line human-readable description of this scheduled task."""
        return (
            f"{self.start_time} — {self.task.name} "
            f"({self.task.duration_minutes} min) "
            f"[{self.task.priority.value}]"
        )


@dataclass
class Pet:
    name: str
    species: str
    breed: str
    age: int
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_name: str) -> None:
        """Remove the task with the given name from this pet's task list."""
        self.tasks = [t for t in self.tasks if t.name != task_name]

    def get_tasks_by_priority(self) -> List[Task]:
        """Return this pet's tasks sorted from highest to lowest priority."""
        order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        return sorted(self.tasks, key=lambda t: order[t.priority])


@dataclass
class Owner:
    name: str
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's pet list."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> None:
        """Remove the pet with the given name from this owner's pet list."""
        self.pets = [p for p in self.pets if p.name != pet_name]

    def get_pet(self, pet_name: str) -> Optional[Pet]:
        """Return the pet with the given name, or None if not found."""
        for pet in self.pets:
            if pet.name == pet_name:
                return pet
        return None

    def get_all_tasks(self) -> List[Tuple[Pet, Task]]:
        """Return every (pet, task) pair across all of this owner's pets."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]


@dataclass
class Constraint:
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    # Each tuple is a (start, end) blocked window e.g. ("12:00", "13:00")
    blocked_times: List[Tuple[str, str]] = field(default_factory=list)

    @staticmethod
    def _to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    def compute_available_minutes(self) -> int:
        """Return total free minutes in the window after subtracting blocked periods."""
        total = self._to_minutes(self.end_time) - self._to_minutes(self.start_time)
        for block_start, block_end in self.blocked_times:
            total -= self._to_minutes(block_end) - self._to_minutes(block_start)
        return max(0, total)

    def is_time_available(self, start: str, duration: int) -> bool:
        """Return True if the given start time + duration fits inside the window with no conflicts."""
        start_min = self._to_minutes(start)
        end_min = start_min + duration
        if start_min < self._to_minutes(self.start_time):
            return False
        if end_min > self._to_minutes(self.end_time):
            return False
        for block_start, block_end in self.blocked_times:
            bs = self._to_minutes(block_start)
            be = self._to_minutes(block_end)
            if start_min < be and end_min > bs:
                return False
        return True


@dataclass
class DailyPlanner:
    date: str
    owner: Owner          # reference to owner gives access to all pets for a unified daily plan
    constraints: Constraint
    scheduled_tasks: List[ScheduledTask] = field(default_factory=list)

    @staticmethod
    def _to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    @staticmethod
    def _to_time_str(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _find_next_free_slot(
        self, from_minute: int, duration: int, occupied: List[Tuple[int, int]], window_end: int
    ) -> Optional[int]:
        """Return the earliest free start minute at or after from_minute that fits duration, or None."""
        cursor = from_minute
        changed = True
        while changed:
            changed = False
            for start, end in occupied:
                if cursor < end and cursor + duration > start:
                    cursor = end
                    changed = True
        return cursor if cursor + duration <= window_end else None

    def sort_by_priority(self, tasks: List[Task]) -> List[Task]:
        """Return tasks sorted from highest to lowest priority."""
        order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        return sorted(tasks, key=lambda t: order[t.priority])

    def sort_by_time(self, tasks: List[Task]) -> List[Task]:
        """Return tasks sorted by pinned_start_time in ascending order.

        Tasks without a pinned_start_time (unpinned) are sorted to the end
        of the list using float("inf") as a sentinel key so they never
        displace time-locked tasks.

        Args:
            tasks: A list of Task objects to sort, may include unpinned tasks.

        Returns:
            A new sorted list; the original list is not modified.
        """
        return sorted(
            tasks,
            key=lambda t: self._to_minutes(t.pinned_start_time) if t.pinned_start_time else float("inf")
        )

    def filter_tasks(
        self,
        completed: Optional[bool] = None,
        pet_name: Optional[str] = None,
    ) -> List[Task]:
        """Return tasks filtered by completion status and/or pet name.

        Both parameters are optional and can be combined. Passing neither
        returns every task across all pets. Passing both applies both
        filters at the same time (AND logic, not OR).

        Args:
            completed: If True, return only completed tasks. If False, return
                       only incomplete tasks. If None, completion is not filtered.
            pet_name:  If provided, return only tasks belonging to the pet with
                       this name. If None, tasks from all pets are included.

        Returns:
            A flat list of Task objects matching all supplied filters.
        """
        results = []
        for pet, task in self.owner.get_all_tasks():
            if pet_name is not None and pet.name != pet_name:
                continue
            if completed is not None and task.completed != completed:
                continue
            results.append(task)
        return results

    def filter_by_time(self, tasks: List[Task]) -> List[Task]:
        """Return only the tasks that cumulatively fit within the available time window."""
        available = self.constraints.compute_available_minutes()
        used = 0
        result = []
        for task in tasks:
            if used + task.duration_minutes <= available:
                result.append(task)
                used += task.duration_minutes
        return result

    def _detect_conflicts(self) -> None:
        """Warn if any two tasks for the same pet have overlapping scheduled times.

        Groups scheduled tasks by pet, then checks each pet's task list for
        adjacent time overlaps. Because self.scheduled_tasks is already sorted
        by start_time, grouping by pet preserves that order — no re-sort is
        needed, keeping this method O(n).

        A conflict exists when one task's end_time is later than the next
        task's start_time (i.e. the same pet is expected in two places at once).
        Issues a UserWarning per conflict rather than raising an exception so
        the rest of the plan can still be displayed.
        """
        # self.scheduled_tasks is already sorted by start_time, so grouping by pet
        # preserves time order within each pet's list — no re-sort needed. O(n) total.
        tasks_by_pet: Dict[str, List[ScheduledTask]] = defaultdict(list)
        for scheduled_task in self.scheduled_tasks:
            tasks_by_pet[scheduled_task.pet_name].append(scheduled_task)

        for pet_name, pet_task_slots in tasks_by_pet.items():
            for current_slot, next_slot in zip(pet_task_slots, pet_task_slots[1:]):
                if current_slot.end_time > next_slot.start_time:
                    warnings.warn(
                        f"Scheduling conflict for {pet_name}: "
                        f"'{current_slot.task.name}' ({current_slot.start_time}–{current_slot.end_time}) overlaps "
                        f"'{next_slot.task.name}' ({next_slot.start_time}–{next_slot.end_time})",
                        UserWarning,
                        stacklevel=2,
                    )

    def generate_plan(self) -> List[ScheduledTask]:
        """Build and return today's schedule, pinning fixed tasks and greedily filling the rest."""
        all_pet_tasks = [
            (pet, task)
            for pet in self.owner.pets
            for task in pet.tasks
            if not task.completed
        ]

        pinned   = [(p, t) for p, t in all_pet_tasks if t.pinned_start_time is not None]
        unpinned = [(p, t) for p, t in all_pet_tasks if t.pinned_start_time is None]

        # Place pinned tasks at their exact requested times
        scheduled_pinned: List[ScheduledTask] = []
        for pet, task in sorted(pinned, key=lambda pt: self._to_minutes(pt[1].pinned_start_time)):
            try:
                start_min = self._to_minutes(task.pinned_start_time)
            except (ValueError, AttributeError) as e:
                warnings.warn(
                    f"Skipping '{task.name}': invalid pinned_start_time "
                    f"'{task.pinned_start_time}' — {e}",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            scheduled_pinned.append(ScheduledTask(
                task=task,
                start_time=self._to_time_str(start_min),
                end_time=self._to_time_str(start_min + task.duration_minutes),
                pet_name=pet.name,
            ))

        # Build occupied intervals from pinned tasks + blocked windows
        occupied: List[Tuple[int, int]] = sorted(
            [(self._to_minutes(st.start_time), self._to_minutes(st.end_time)) for st in scheduled_pinned]
            + [(self._to_minutes(bs), self._to_minutes(be)) for bs, be in self.constraints.blocked_times]
        )

        # Greedily fit unpinned tasks into the remaining free slots
        scheduled_unpinned: List[ScheduledTask] = []
        window_end = self._to_minutes(self.constraints.end_time)
        cursor = self._to_minutes(self.constraints.start_time)

        priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        for pet, task in sorted(unpinned, key=lambda pt: priority_order[pt[1].priority]):
            slot = self._find_next_free_slot(cursor, task.duration_minutes, occupied, window_end)
            if slot is None:
                warnings.warn(
                    f"No available slot for '{task.name}' ({task.duration_minutes} min) — skipping.",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            end = slot + task.duration_minutes
            scheduled_unpinned.append(ScheduledTask(
                task=task,
                start_time=self._to_time_str(slot),
                end_time=self._to_time_str(end),
                pet_name=pet.name,
            ))
            occupied.append((slot, end))
            occupied.sort()
            cursor = end

        self.scheduled_tasks = sorted(
            scheduled_pinned + scheduled_unpinned,
            key=lambda st: self._to_minutes(st.start_time),
        )
        self._detect_conflicts()
        return self.scheduled_tasks

    def complete_task(self, pet: Pet, task: Task) -> Optional[Task]:
        """Mark a task as complete and automatically queue its next occurrence if recurring.

        For recurring tasks with a frequency of "daily" or "weekly", calls
        next_occurrence() to create a fresh copy of the task with an updated
        due_date, then adds it directly to the pet's task list so it appears
        in the next call to generate_plan().

        Args:
            pet:  The Pet that owns the task. Required so the next occurrence
                  can be added back to the correct pet's task list.
            task: The Task to mark complete.

        Returns:
            The newly created next-occurrence Task if the task is recurring,
            or None if the task is non-recurring and no follow-up is needed.
        """
        task.mark_complete()
        if task.recurring and task.frequency in ("daily", "weekly"):
            next_task = task.next_occurrence(self.date)
            pet.add_task(next_task)
            return next_task
        return None

    def display_plan(self) -> str:
        """Return the full daily schedule as a formatted string."""
        if not self.scheduled_tasks:
            return "No tasks scheduled for today."
        lines = [f"Daily plan for {self.owner.name} — {self.date}:"]
        for st in self.scheduled_tasks:
            lines.append(f"  {st.get_summary()}")
        return "\n".join(lines)


@dataclass
class AIAssistant:
    model: str
    planner: Optional[DailyPlanner] = None

    def explain_plan(self, plan: List[ScheduledTask]) -> str:
        """Ask Claude to explain the schedule in a friendly, readable way."""
        if not plan:
            return "No tasks were scheduled today — try adding more tasks or expanding available time."
        plan_text = "\n".join(st.get_summary() for st in plan)
        client = anthropic.Anthropic()
        message = client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a friendly pet care assistant. Explain this daily pet care schedule "
                        "in a warm, helpful tone. Briefly note why the order of tasks makes sense:\n\n"
                        f"{plan_text}"
                    ),
                }
            ],
        )
        return message.content[0].text

    def suggest_tasks(self, pet: Pet) -> List[Task]:
        """Ask Claude to suggest care tasks for the given pet and return them as Task objects."""
        client = anthropic.Anthropic()
        prompt = (
            f"Suggest 3-5 daily care tasks for a {pet.age}-year-old {pet.breed} {pet.species} named {pet.name}. "
            "Return ONLY a valid JSON array. Each object must have: "
            "name (str), category (str), duration_minutes (int), priority (low/medium/high), "
            "recurring (bool), frequency (daily/weekly or null).\n"
            'Example: [{"name":"Morning walk","category":"exercise","duration_minutes":30,'
            '"priority":"high","recurring":true,"frequency":"daily"}]'
        )
        message = client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            tasks_data = json.loads(message.content[0].text)
            return [
                Task(
                    name=t["name"],
                    category=t["category"],
                    duration_minutes=t["duration_minutes"],
                    priority=Priority[t["priority"].upper()],
                    recurring=t.get("recurring", False),
                    frequency=t.get("frequency"),
                )
                for t in tasks_data
            ]
        except (json.JSONDecodeError, KeyError):
            return []

    def generate_and_explain(
        self,
        owner: Owner,
        constraints: Constraint,
        date: Optional[str] = None,
    ) -> str:
        """Generate today's schedule for the owner and return Claude's explanation of it."""
        plan_date = date or datetime.today().strftime("%Y-%m-%d")
        self.planner = DailyPlanner(
            date=plan_date,
            owner=owner,
            constraints=constraints,
        )
        plan = self.planner.generate_plan()
        return self.explain_plan(plan)
