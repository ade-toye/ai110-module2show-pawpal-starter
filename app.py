import streamlit as st
from datetime import date, datetime
from pawpal_system import Owner, Pet, Task, Constraint, DailyPlanner, AIAssistant, Priority

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ── Session state init ──────────────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = None

if "plan" not in st.session_state:
    st.session_state.plan = None

if "planner" not in st.session_state:
    st.session_state.planner = None

# ── 1. Owner & Pet Setup ────────────────────────────────────────────────────
st.subheader("Owner & Pet Info")

owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")

col1, col2, col3 = st.columns(3)
with col1:
    species = st.selectbox("Species", ["dog", "cat", "bird", "other"])
with col2:
    breed = st.text_input("Breed", value="Mixed")
with col3:
    age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)

if st.button("Save owner & pet"):
    pet = Pet(name=pet_name, species=species, breed=breed, age=int(age))
    owner = Owner(name=owner_name)
    owner.add_pet(pet)
    st.session_state.owner = owner
    st.session_state.plan = None
    st.success(f"Saved! {owner_name} owns {pet_name} the {species}.")

st.divider()

# ── 2. Add Tasks ────────────────────────────────────────────────────────────
st.subheader("Add a Task")

if st.session_state.owner is None:
    st.info("Set up an owner and pet above first.")
else:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        task_name = st.text_input("Task", value="Morning walk")
    with col2:
        category = st.selectbox("Category", ["exercise", "feeding", "grooming", "health", "enrichment", "other"])
    with col3:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with col4:
        priority = st.selectbox("Priority", ["high", "medium", "low"])

    pet_names = [p.name for p in st.session_state.owner.pets]
    target_pet = st.selectbox("Pet", pet_names)

    pinned = st.checkbox("Pin to exact time?")
    pinned_time = None
    if pinned:
        pinned_time = st.time_input("Start time").strftime("%H:%M")

    if st.button("Add task"):
        pet = st.session_state.owner.get_pet(target_pet)
        task = Task(
            name=task_name,
            category=category,
            duration_minutes=int(duration),
            priority=Priority[priority.upper()],
            pinned_start_time=pinned_time,
        )
        pet.add_task(task)
        st.success(f"Added '{task_name}' to {target_pet}.")

    all_tasks = st.session_state.owner.get_all_tasks()
    if all_tasks:
        st.write("Current tasks:")
        st.table([
            {
                "Pet": p.name,
                "Task": t.name,
                "Category": t.category,
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority.value,
                "Pinned at": t.pinned_start_time or "—",
            }
            for p, t in all_tasks
        ])
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

# ── 3. Generate Schedule ────────────────────────────────────────────────────
st.subheader("Generate Schedule")

if st.session_state.owner is None:
    st.info("Set up an owner and pet above first.")
else:
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.time_input("Available from", value=datetime.strptime("08:00", "%H:%M").time())
    with col2:
        end_time = st.time_input("Available until", value=datetime.strptime("20:00", "%H:%M").time())

    if st.button("Generate schedule"):
        constraints = Constraint(
            start_time=start_time.strftime("%H:%M"),
            end_time=end_time.strftime("%H:%M"),
        )
        planner = DailyPlanner(
            date=date.today().strftime("%Y-%m-%d"),
            owner=st.session_state.owner,
            constraints=constraints,
        )
        st.session_state.plan = planner.generate_plan()
        st.session_state.planner = planner

    if st.session_state.plan is not None:
        st.text(st.session_state.planner.display_plan())

        if st.button("Explain this plan with AI"):
            ai = AIAssistant(model="claude-sonnet-4-6")
            explanation = ai.explain_plan(st.session_state.plan)
            st.markdown(explanation)
