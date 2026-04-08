import streamlit as st
from database import init_db, get_connection
from datetime import datetime, timedelta
import os
from streamlit_autorefresh import st_autorefresh

# ---------------- INIT ---------------- #
init_db()

st.set_page_config(page_title="Quiz App", layout="centered")

# Ensure image folder exists
if not os.path.exists("images"):
    os.makedirs("images")

# ---------------- LOGIN CONTROL ---------------- #

def is_login_enabled():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT is_enabled, enabled_at FROM login_control WHERE id=1")
    row = cursor.fetchone()

    if row:
        is_enabled, enabled_at = row

        if is_enabled and enabled_at:
            enabled_time = datetime.fromisoformat(enabled_at)
            if datetime.now() > enabled_time + timedelta(minutes=30):
                cursor.execute("UPDATE login_control SET is_enabled=0 WHERE id=1")
                conn.commit()
                conn.close()
                return False

        conn.close()
        return bool(is_enabled)

    conn.close()
    return False

def enable_login():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE login_control SET is_enabled=1, enabled_at=? WHERE id=1",
        (datetime.now().isoformat(),)
    )
    conn.commit()
    conn.close()

def disable_login():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE login_control SET is_enabled=0 WHERE id=1")
    conn.commit()
    conn.close()

# ---------------- SESSION ---------------- #

if "role" not in st.session_state:
    st.session_state.role = None

if "admin_page" not in st.session_state:
    st.session_state.admin_page = None

# ---------------- LOGIN PAGE ---------------- #

st.title("🧠 Quiz Application")

if st.session_state.role is None:

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # ADMIN LOGIN
        if username.lower() == "admin":
            if password == "Admin#123":
                st.session_state.role = "admin"
                st.success("Admin Login Successful")
                st.rerun()
            else:
                st.error("Invalid Admin Password")

        # USER LOGIN
        else:
            if not is_login_enabled():
                st.error("User login is disabled by Admin")
            elif password == "Login#123":
                st.session_state.role = "user"
                st.success("User Login Successful")
                st.rerun()
            else:
                st.error("Invalid User Password")

# ---------------- ADMIN PANEL ---------------- #

elif st.session_state.role == "admin":

    st.subheader("Admin Dashboard")

    col1, col2 = st.columns(2)

    if col1.button("➕ Create New Test"):
        st.session_state.admin_page = "create"

    if col2.button("📋 Manage Tests"):
        st.session_state.admin_page = "manage"

    if col1.button("📊 View Results"):
        st.session_state.admin_page = "results"

    if col2.button("🔐 Enable/Disable Login"):
        st.session_state.admin_page = "login_control"

    st.divider()

    # ---------------- LOGIN CONTROL ---------------- #
    if st.session_state.admin_page == "login_control":

        st.subheader("Login Control")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Enable Login"):
                enable_login()
                st.success("Login enabled for 30 minutes")

        with col2:
            if st.button("Disable Login"):
                disable_login()
                st.warning("Login disabled")

    # ---------------- CREATE TEST ---------------- #
    elif st.session_state.admin_page == "create":

        st.subheader("Create New Test")

        test_id = st.text_input("Test ID")
        remarks = st.text_input("Remarks")
        total_questions = st.number_input("Number of Questions", min_value=1, step=1)
        time_limit = st.number_input("Time Limit (minutes)", min_value=1, step=1)

        if st.button("Create Test"):

            conn = get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO tests (test_id, remarks, total_questions, time_limit)
                    VALUES (?, ?, ?, ?)
                """, (test_id, remarks, total_questions, time_limit))

                conn.commit()

                st.session_state.current_test = test_id
                st.session_state.q_count = 0
                st.session_state.total_q = total_questions

                st.success("Test Created Successfully!")

            except:
                st.error("Test ID already exists!")

            conn.close()

        # -------- ADD QUESTIONS -------- #
        if "current_test" in st.session_state:

            st.divider()

            q_no = st.session_state.q_count + 1
            total_q = st.session_state.total_q

            if q_no <= total_q:

                st.subheader(f"Question {q_no} of {total_q}")

                q_text = st.text_area("Question Text", key=f"q_{q_no}")
                uploaded_image = st.file_uploader("Upload Image", type=["png","jpg","jpeg"], key=f"img_{q_no}")

                option_a = st.text_input("Option A", key=f"a_{q_no}")
                option_b = st.text_input("Option B", key=f"b_{q_no}")
                option_c = st.text_input("Option C", key=f"c_{q_no}")
                option_d = st.text_input("Option D", key=f"d_{q_no}")

                correct_option = st.selectbox("Correct Answer", ["A","B","C","D"], key=f"ans_{q_no}")

                if st.button("Save Question"):

                    image_path = None

                    if uploaded_image:
                        image_path = f"images/{uploaded_image.name}"
                        with open(image_path, "wb") as f:
                            f.write(uploaded_image.getbuffer())

                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO questions 
                        (test_id, question_text, image_path, option_a, option_b, option_c, option_d, correct_option)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        st.session_state.current_test,
                        q_text,
                        image_path,
                        option_a,
                        option_b,
                        option_c,
                        option_d,
                        correct_option
                    ))

                    conn.commit()
                    conn.close()

                    st.session_state.q_count += 1
                    st.success(f"Question {q_no} saved!")

                    # Clear inputs
                    for key in list(st.session_state.keys()):
                        if key.startswith((f"q_{q_no}", f"img_{q_no}", f"a_{q_no}", f"b_{q_no}", f"c_{q_no}", f"d_{q_no}", f"ans_{q_no}")):
                            del st.session_state[key]

                    st.rerun()

            else:
                st.success("All questions added successfully!")

    # ---------------- PLACEHOLDERS ---------------- #
    elif st.session_state.admin_page == "manage":

        st.subheader("Manage Tests")

        conn = get_connection()
        cursor = conn.cursor()

        # Get all tests
        cursor.execute("SELECT * FROM tests")
        tests = cursor.fetchall()

        for test in tests:

            test_id = test[0]
            remarks = test[1]
            created_at = test[4]

            # Count attempts
            cursor.execute("SELECT COUNT(*) FROM results WHERE test_id=?", (test_id,))
            count = cursor.fetchone()[0]

            col1, col2 = st.columns([4,1])

            with col1:
                st.write(f"**Test ID:** {test_id}")
                st.write(f"Remarks: {remarks}")
                st.write(f"Created: {created_at}")
                st.write(f"Attempts: {count}")

            with col2:
                if st.button("Delete", key=f"del_{test_id}"):

                    # Delete test + questions + results
                    cursor.execute("DELETE FROM tests WHERE test_id=?", (test_id,))
                    cursor.execute("DELETE FROM questions WHERE test_id=?", (test_id,))
                    cursor.execute("DELETE FROM results WHERE test_id=?", (test_id,))

                    conn.commit()
                    st.warning(f"{test_id} deleted")
                    st.rerun()

            st.divider()

        conn.close()
    #--------------------View Results-------------#
    elif st.session_state.admin_page == "results":

        st.subheader("View Results")

        conn = get_connection()
        cursor = conn.cursor()

        # Get all test IDs
        cursor.execute("SELECT test_id FROM tests")
        test_ids = [row[0] for row in cursor.fetchall()]

        selected_test = st.selectbox("Select Test ID", [""] + test_ids)

        selected_date = st.date_input("Select Date")

        if selected_test and selected_date:

            date_str = selected_date.strftime("%Y-%m-%d")

            cursor.execute("""
                SELECT name, department, score, timestamp 
                FROM results 
                WHERE test_id=? AND DATE(timestamp)=?
            """, (selected_test, date_str))

            results = cursor.fetchall()

            if results:

                st.subheader("Results")

                for r in results:
                    st.write(f"Name: {r[0]}")
                    st.write(f"Dept: {r[1]}")
                    st.write(f"Score: {r[2]}")
                    st.write(f"Time: {r[3]}")
                    st.divider()

            else:
                st.info("No data found for selected filters")

        conn.close()

    # ---------------- LOGOUT ---------------- #
    st.divider()
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

# ---------------- USER PANEL ---------------- #

elif st.session_state.role == "user":

    # -------- GLOBAL LOGOUT -------- #
    col_top1, col_top2 = st.columns([6,1])
    with col_top2:
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    st.subheader("User Panel")

    # -------- STEP 1: USER DETAILS -------- #
    if "test_started" not in st.session_state:

        name = st.text_input("Enter Your Name")
        dept = st.text_input("Enter Department")
        test_id = st.text_input("Enter Test ID")

        if st.button("Proceed"):

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM tests WHERE test_id=?", (test_id,))
            test = cursor.fetchone()
            conn.close()

            if test:
                st.session_state.test_id = test_id
                st.session_state.name = name
                st.session_state.dept = dept
                st.session_state.instructions = True
                st.session_state.test_started = False
                st.session_state.submitted = False
                st.rerun()
            else:
                st.error("Invalid Test ID")

    # -------- STEP 2: INSTRUCTIONS -------- #
    elif st.session_state.get("instructions"):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT total_questions, time_limit FROM tests WHERE test_id=?",
                       (st.session_state.test_id,))
        total_q, time_limit = cursor.fetchone()
        conn.close()

        st.subheader("Instructions")
        st.write(f"Total Questions: {total_q}")
        st.write(f"Time Limit: {time_limit} minutes")

        if st.button("Start Test"):

            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=time_limit)

            st.session_state.start_time = start_time
            st.session_state.end_time = end_time   # 🔥 FIXED TIMER
            st.session_state.test_started = True
            st.session_state.instructions = False
            st.session_state.current_q = 0
            st.session_state.answers = {}
            st.rerun()

    # -------- STEP 3: TEST -------- #
    elif st.session_state.get("test_started") and not st.session_state.get("submitted"):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM questions WHERE test_id=?",
                       (st.session_state.test_id,))
        questions = cursor.fetchall()

        conn.close()

        total_q = len(questions)

        # -------- AUTO REFRESH -------- #
        st_autorefresh(interval=1000, key="timer_refresh")

        # -------- TIMER -------- #
        remaining = st.session_state.end_time - datetime.now()

        if remaining.total_seconds() <= 0:
            st.warning("Time Up! Auto submitting...")
            st.session_state.submitted = True
            st.rerun()
        else:
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            st.info(f"Time Left: {mins}m {secs}s")

        # -------- QUESTION -------- #
        q_index = st.session_state.current_q
        q = questions[q_index]

        st.subheader(f"Question {q_index+1} of {total_q}")
        st.write(q[2])

        if q[3]:
            st.image(q[3], width=300)

        options = {
            "A": q[4],
            "B": q[5],
            "C": q[6],
            "D": q[7]
        }

        selected = st.session_state.answers.get(q_index, None)

        choice = st.radio(
            "Choose Answer",
            ["A", "B", "C", "D"],
            format_func=lambda x: options[x],
            index=None if selected is None else ["A","B","C","D"].index(selected),
            key=f"q_{q_index}"
        )

        if choice:
            st.session_state.answers[q_index] = choice

        # -------- NAVIGATION -------- #
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Previous") and q_index > 0:
                st.session_state.current_q -= 1
                st.rerun()

        if q_index < total_q - 1:
            with col2:
                if st.button("Next"):
                    st.session_state.current_q += 1
                    st.rerun()

        with col3:
            if st.button("Submit"):
                st.session_state.submitted = True
                st.rerun()

    # -------- STEP 4: RESULT -------- #
    elif st.session_state.get("submitted"):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM questions WHERE test_id=?",
                       (st.session_state.test_id,))
        questions = cursor.fetchall()

        score = 0

        for i, q in enumerate(questions):
            if st.session_state.answers.get(i) == q[8]:
                score += 1

        cursor.execute("""
            INSERT INTO results (name, department, test_id, score)
            VALUES (?, ?, ?, ?)
        """, (
            st.session_state.name,
            st.session_state.dept,
            st.session_state.test_id,
            score
        ))

        conn.commit()
        conn.close()

        st.subheader("Test Submitted!")
        st.success(f"Your Score: {score} / {len(questions)}")

        # Clean test state
        for key in ["test_started", "instructions", "current_q", "answers"]:
            if key in st.session_state:
                del st.session_state[key]

