import streamlit as st

from pawpal_system import CareTask, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")

# --- persist domain objects in the session "vault" -----------------------
# Streamlit reruns this script top-to-bottom on every interaction. Guard the
# creation so the Scheduler/Owner are built ONCE and then reused, instead of
# being reborn empty on each rerun.
if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler()

if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        owner_id=1,
        name="Jordan",
        hours_available_daily=2.0,
        reminders_enabled=True,
    )
    st.session_state.scheduler.add_owner(st.session_state.owner)

# grab the SAME objects every rerun
scheduler = st.session_state.scheduler
owner = st.session_state.owner

# simple monotonic id counters so every Pet/CareTask gets a unique id
if "next_pet_id" not in st.session_state:
    st.session_state.next_pet_id = 1
if "next_task_id" not in st.session_state:
    st.session_state.next_task_id = 1

# map the friendly UI label to the domain's integer priority (1 = highest)
PRIORITY_TO_INT = {"high": 1, "medium": 2, "low": 3}

# --- Add a Pet -----------------------------------------------------------
st.markdown("### Add a Pet")
with st.form("add_pet_form"):
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "other"])
    breed = st.text_input("Breed", value="Shiba Inu")
    col_a, col_b = st.columns(2)
    with col_a:
        age = st.number_input("Age (years)", min_value=0, max_value=40, value=3)
    with col_b:
        weight = st.number_input("Weight (kg)", min_value=0.1, value=9.0)
    add_pet_clicked = st.form_submit_button("Add pet")

if add_pet_clicked:
    pet = Pet(
        pet_id=st.session_state.next_pet_id,
        name=pet_name,
        species=species,
        breed=breed,
        age=int(age),
        weight=float(weight),
    )
    owner.add_pet(pet)                      # <-- Owner owns pets
    st.session_state.next_pet_id += 1
    st.success(f"Added {pet.get_pet_info()}")

# show the current pets (read back from the persisted owner)
if owner.pets:
    st.write("Current pets:")
    st.table(
        [
            {"id": p.pet_id, "name": p.name, "species": p.species,
             "breed": p.breed, "age": p.age, "weight": p.weight,
             "tasks": len(p.tasks)}
            for p in owner.pets
        ]
    )
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Add a Care Task -----------------------------------------------------
st.markdown("### Add a Care Task")
if not owner.pets:
    st.info("Add a pet first, then you can schedule tasks for it.")
else:
    with st.form("add_task_form"):
        # pick which pet this task belongs to
        pet_choice = st.selectbox(
            "For which pet?",
            options=owner.pets,
            format_func=lambda p: f"{p.name} ({p.species})",
        )
        description = st.text_input("Task description", value="Morning walk")
        col1, col2, col3 = st.columns(3)
        with col1:
            time = st.text_input("Time (HH:MM)", value="08:00")
        with col2:
            category = st.selectbox(
                "Category", ["feeding", "walk", "medication", "grooming"]
            )
        with col3:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly"])
        add_task_clicked = st.form_submit_button("Add task")

    if add_task_clicked:
        task = CareTask(
            task_id=st.session_state.next_task_id,
            description=description,
            time=time,
            frequency=frequency,
            category=category,
            priority=PRIORITY_TO_INT[priority],
        )
        pet_choice.add_task(task)          # <-- Pet owns tasks
        st.session_state.next_task_id += 1
        st.success(f"Added task to {pet_choice.name}: {task.summary()}")

st.divider()

# --- Build Schedule ------------------------------------------------------
st.subheader("Build Schedule")
st.caption("Calls the Scheduler to order pending tasks across all pets.")

if st.button("Generate schedule"):
    pending = scheduler.get_pending_tasks()   # <-- Scheduler is the 'brain'
    if not pending:
        st.info("No pending tasks. Add some tasks above.")
    else:
        st.write(f"{len(pending)} pending task(s), highest priority first:")
        for task in pending:
            st.markdown(f"- {task.summary()}")
