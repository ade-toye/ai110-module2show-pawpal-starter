from pawpal_system import Owner, Pet, Task, Constraint, DailyPlanner, Priority
from datetime import date, datetime
import warnings


# ── Input helpers ──────────────────────────────────────────────────────────────

def get_str(prompt: str) -> str:
    """Ask for a non-empty string, re-prompting until one is provided."""
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("  This field cannot be empty. Please try again.\n")


def get_int(prompt: str, min_val: int = 1) -> int:
    """Ask for an integer >= min_val, re-prompting on bad input."""
    while True:
        try:
            val = int(input(prompt).strip())
            if val >= min_val:
                return val
            print(f"  Please enter a number of at least {min_val}.\n")
        except ValueError:
            print("  Please enter a whole number.\n")


def get_choice(prompt: str, choices: list) -> str:
    """Ask the user to pick from a list of choices (case-insensitive)."""
    display = " / ".join(choices)
    while True:
        val = input(f"{prompt} [{display}]: ").strip().lower()
        if val in [c.lower() for c in choices]:
            return val
        print(f"  Invalid choice. Please enter one of: {display}\n")


def get_yes_no(prompt: str) -> bool:
    """Return True for 'y', False for 'n'."""
    return get_choice(prompt, ["y", "n"]) == "y"


def get_time(prompt: str) -> str:
    """Ask for a time in HH:MM format, re-prompting until valid."""
    while True:
        val = input(f"{prompt} (HH:MM, e.g. 17:00): ").strip()
        parts = val.split(":")
        if len(parts) == 2:
            try:
                h, m = int(parts[0]), int(parts[1])
                if 0 <= h <= 23 and 0 <= m <= 59:
                    return f"{h:02d}:{m:02d}"
            except ValueError:
                pass
        print("  Please enter a valid time in HH:MM format (e.g. 09:30).\n")


def get_date() -> str:
    """Ask for a date in YYYY-MM-DD format, defaulting to today on blank input."""
    today = date.today().strftime("%Y-%m-%d")
    val = input(f"Schedule date (YYYY-MM-DD) [press Enter for today, {today}]: ").strip()
    if not val:
        return today
    try:
        datetime.strptime(val, "%Y-%m-%d")
        return val
    except ValueError:
        print(f"  Invalid date format — using today ({today}).\n")
        return today


# ── Section builders ───────────────────────────────────────────────────────────

def build_task(index: int) -> Task:
    """Interactively collect all fields for a single Task."""
    print(f"\n  -- Task {index} --")
    name     = get_str(   "    Task name                              : ")
    category = get_str(   "    Category (e.g. feeding, exercise)      : ")
    duration = get_int(   "    Duration (minutes)                     : ", min_val=1)
    priority = get_choice("    Priority                               ", ["low", "medium", "high"])

    pinned_time = None
    if get_yes_no("    Pin to a specific start time?          "):
        pinned_time = get_time("    Start time                            ")

    recurring = False
    frequency = None
    if get_yes_no("    Is this a recurring task?               "):
        recurring = True
        frequency = get_choice("    Frequency                             ", ["daily", "weekly"])

    return Task(
        name=name,
        category=category,
        duration_minutes=duration,
        priority=Priority[priority.upper()],
        pinned_start_time=pinned_time,
        recurring=recurring,
        frequency=frequency,
    )


def build_pet(index: int) -> Pet:
    """Interactively collect all fields for a Pet and its tasks."""
    print(f"\n-- Pet {index} --")
    name    = get_str("  Name                                    : ")
    species = get_str("  Species (e.g. dog, cat, parrot)         : ")
    breed   = get_str("  Breed                                   : ")
    age     = get_int("  Age (years)                             : ", min_val=0)

    pet = Pet(name=name, species=species, breed=breed, age=age)

    print(f"\n  How many tasks does {name} have?")
    task_count = get_int("  Number of tasks                         : ", min_val=1)
    for i in range(1, task_count + 1):
        pet.add_task(build_task(i))

    return pet


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n========================================")
    print("        Welcome to PawPal Planner!")
    print("========================================\n")
    print("Follow the prompts to build your pet care")
    print("schedule. Press Ctrl+C at any time to quit.\n")

    # Owner
    print("=== Step 1: Owner ===")
    owner = Owner(name=get_str("Your name: "))

    # Pets
    print("\n=== Step 2: Your Pets ===")
    pet_count = get_int("How many pets do you have? ", min_val=1)
    for i in range(1, pet_count + 1):
        owner.add_pet(build_pet(i))

    # Schedule window
    print("\n=== Step 3: Schedule Window ===")
    start_time = get_time("Window start time")
    end_time   = get_time("Window end time  ")

    # Date
    print("\n=== Step 4: Date ===")
    plan_date = get_date()

    # Build and display plan
    print("\n========================================")
    print("            Generating Plan...")
    print("========================================\n")

    constraints = Constraint(start_time=start_time, end_time=end_time)
    planner = DailyPlanner(date=plan_date, owner=owner, constraints=constraints)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        planner.generate_plan()

    if caught:
        print("Warnings:")
        for w in caught:
            print(f"  [!] {w.message}")
        print()

    print(planner.display_plan())
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting PawPal. Goodbye!")
