import streamlit as st
from database import init_db, get_connection
from datetime import datetime, timedelta
import os
import pandas as pd
from streamlit_autorefresh import st_autorefresh
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppDeployButton {display: none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
# ---------------- CONFIG & STYLING ---------------- #
st.set_page_config(page_title="ProQuiz | Dark Edition", layout="wide", page_icon="🎓")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4, p, label, .stMarkdown { color: #E0E0E0 !important; }
    [data-testid="stMetricValue"] { color: #00D4FF !important; font-weight: bold !important; }
    [data-testid="stMetricLabel"] { color: #8B949E !important; }
    .stButton>button { border-radius: 8px; font-weight: 600; }
    section[data-testid="stSidebar"] { background-color: #161B22; }
    /* Table styling for dark mode */
    .stDataFrame { border: 1px solid #30363D; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ---------------- DB HELPERS ---------------- #
init_db()
if not os.path.exists("images"):
    os.makedirs("images")

def is_login_enabled():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_enabled, enabled_at FROM login_control WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    if row:
        is_enabled, enabled_at = row
        if is_enabled and enabled_at:
            enabled_time = datetime.fromisoformat(enabled_at)
            if datetime.now() > enabled_time + timedelta(minutes=30):
                conn = get_connection(); c = conn.cursor()
                c.execute("UPDATE login_control SET is_enabled=0 WHERE id=1")
                conn.commit(); conn.close()
                return False
        return bool(is_enabled)
    return False

# ---------------- SESSION ---------------- #
if "role" not in st.session_state:
    st.session_state.role = None

# ---------------- LOGIN PAGE ---------------- #
if st.session_state.role is None:
    _, center, _ = st.columns([1, 1.5, 1])
    with center:
        st.markdown("<h1 style='text-align: center; color: #58A6FF !important;'>⚡ ProQuiz Portal</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Sign In", use_container_width=True):
                if username.lower() == "admin" and password == "Admin#123":
                    st.session_state.role = "admin"
                    st.rerun()
                elif username.lower() != "admin" and is_login_enabled() and password == "Login#123":
                    st.session_state.role = "user"
                    st.rerun()
                else:
                    st.error("Invalid Credentials or Login Disabled")

# ---------------- ADMIN PANEL ---------------- #
elif st.session_state.role == "admin":
    with st.sidebar:
        st.markdown("### 🛠 Admin Controls")
        if st.button("🚪 Logout", key="admin_logout"):
            st.session_state.clear()
            st.rerun()

    st.title("Manager Dashboard")
    t1, t2, t3, t4 = st.tabs(["🆕 Create Test", "📂 Manage Tests", "📈 View Results", "🔒 Access Control"])

    with t1: # Create Test
        with st.form("new_test"):
            t_id = st.text_input("Test ID")
            t_rem = st.text_input("Remarks")
            t_q = st.number_input("Total Questions", min_value=1, step=1)
            t_l = st.number_input("Time Limit (min)", min_value=1, step=1)
            if st.form_submit_button("Initialize"):
                conn = get_connection(); cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO tests (test_id, remarks, total_questions, time_limit) VALUES (?,?,?,?)", (t_id, t_rem, t_q, t_l))
                    conn.commit()
                    st.session_state.current_test, st.session_state.q_count, st.session_state.total_q = t_id, 0, t_q
                    st.success("Test Skeleton Created!")
                except: st.error("ID already exists")
                conn.close()

        if "current_test" in st.session_state:
            q_no = st.session_state.q_count + 1
            if q_no <= st.session_state.total_q:
                st.subheader(f"Question {q_no}")
                q_txt = st.text_area("Question Text")
                q_img = st.file_uploader("Upload Image", type=["png","jpg","jpeg"])
                o1, o2 = st.columns(2)
                oa, ob, oc, od = o1.text_input("A"), o2.text_input("B"), o1.text_input("C"), o2.text_input("D")
                correct = st.selectbox("Correct Option", ["A","B","C","D"])
                if st.button("Save Question"):
                    path = None
                    if q_img:
                        path = f"images/{q_img.name}"
                        with open(path, "wb") as f: f.write(q_img.getbuffer())
                    conn = get_connection(); cursor = conn.cursor()
                    cursor.execute("INSERT INTO questions (test_id, question_text, image_path, option_a, option_b, option_c, option_d, correct_option) VALUES (?,?,?,?,?,?,?,?)",
                                   (st.session_state.current_test, q_txt, path, oa, ob, oc, od, correct))
                    conn.commit(); conn.close()
                    st.session_state.q_count += 1; st.rerun()
            else:
                st.success("All questions added!")
                if st.button("Finish Building"): st.session_state.pop("current_test"); st.rerun()

    with t2: # Manage Tests (Cascading Deletion)
        st.subheader("Manage Active Tests")
        conn = get_connection(); cursor = conn.cursor()
        tests = cursor.execute("SELECT * FROM tests").fetchall()
        for t in tests:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                c1.write(f"**Test ID:** {t[0]} | **Remarks:** {t[1]}")
                if c2.button("🗑 Delete", key=f"del_{t[0]}"):
                    # Crucial: Delete from ALL related tables to prevent ghost data
                    cursor.execute("DELETE FROM tests WHERE test_id=?", (t[0],))
                    cursor.execute("DELETE FROM questions WHERE test_id=?", (t[0],))
                    cursor.execute("DELETE FROM results WHERE test_id=?", (t[0],))
                    conn.commit(); st.rerun()
        conn.close()

    with t3: # Results (Dual Filter)
        st.subheader("Performance Explorer")
        conn = get_connection(); cursor = conn.cursor()
        avail_tids = [r[0] for r in cursor.execute("SELECT DISTINCT test_id FROM results").fetchall()]
        avail_names = [r[0] for r in cursor.execute("SELECT DISTINCT name FROM results").fetchall()]
        
        c1, c2 = st.columns(2)
        sel_test = c1.selectbox("Filter by Test ID", ["All Tests"] + avail_tids)
        sel_name = c2.selectbox("Filter by Name", ["All Names"] + avail_names)
        
        query = "SELECT name, department, test_id, score, timestamp FROM results WHERE 1=1"
        params = []
        if sel_test != "All Tests": query += " AND test_id = ?"; params.append(sel_test)
        if sel_name != "All Names": query += " AND name = ?"; params.append(sel_name)
        
        res = cursor.execute(query + " ORDER BY timestamp DESC", params).fetchall()
        if res:
            df = pd.DataFrame(res, columns=["Candidate", "Dept", "Test ID", "Score", "Date/Time"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No matching results found in the database.")
        conn.close()

    with t4: # Access Control
        st.subheader("User Login Access")
        status = "🟢 Enabled" if is_login_enabled() else "🔴 Disabled"
        st.write(f"Current Access: **{status}**")
        if st.button("Enable Login (30m)"):
            conn = get_connection(); cur = conn.cursor()
            cur.execute("UPDATE login_control SET is_enabled=1, enabled_at=? WHERE id=1", (datetime.now().isoformat(),))
            conn.commit(); conn.close(); st.rerun()
        if st.button("Disable Login"):
            conn = get_connection(); cur = conn.cursor()
            cur.execute("UPDATE login_control SET is_enabled=0 WHERE id=1")
            conn.commit(); conn.close(); st.rerun()

# ---------------- USER PANEL ---------------- #
elif st.session_state.role == "user":
    with st.sidebar:
        if st.button("🚪 Logout", key="user_logout"):
            st.session_state.clear(); st.rerun()

    if "test_id" not in st.session_state:
        _, cent, _ = st.columns([1, 1.5, 1])
        with cent:
            st.markdown("### 📝 Entry Form")
            with st.container(border=True):
                n = st.text_input("Name")
                d = st.text_input("Department")
                ti = st.text_input("Test ID")
                if st.button("Enter Test", use_container_width=True):
                    conn = get_connection(); cursor = conn.cursor()
                    test = cursor.execute("SELECT * FROM tests WHERE test_id=?", (ti,)).fetchone()
                    conn.close()
                    if test:
                        st.session_state.update({"test_id": ti, "name": n, "dept": d, "submitted": False, "result_saved": False})
                        st.rerun()
                    else: st.error("Test ID not found.")

    elif st.session_state.get("test_id") and not st.session_state.get("submitted"):
        if "end_time" not in st.session_state:
            conn = get_connection(); cursor = conn.cursor()
            t_data = cursor.execute("SELECT time_limit FROM tests WHERE test_id=?", (st.session_state.test_id,)).fetchone()
            conn.close()
            st.session_state.end_time = datetime.now() + timedelta(minutes=t_data[0])
            st.session_state.current_q, st.session_state.answers = 0, {}

        st_autorefresh(interval=1000, key="timer_refresh")
        rem = st.session_state.end_time - datetime.now()
        if rem.total_seconds() <= 0:
            st.session_state.submitted = True; st.rerun()

        conn = get_connection(); cursor = conn.cursor()
        qs = cursor.execute("SELECT * FROM questions WHERE test_id=?", (st.session_state.test_id,)).fetchall()
        conn.close()

        st.metric("⌛ Timer", f"{int(rem.total_seconds()//60)}m {int(rem.total_seconds()%60)}s")
        q = qs[st.session_state.current_q]
        with st.container(border=True):
            st.markdown(f"#### Question {st.session_state.current_q + 1}")
            st.write(q[2])
            if q[3]: st.image(q[3], width=300)
            ans = st.radio("Select Answer:", ["A","B","C","D"], 
                           format_func=lambda x: f"{x}: {q[4 if x=='A' else 5 if x=='B' else 6 if x=='C' else 7]}",
                           index=None if st.session_state.current_q not in st.session_state.answers else ["A","B","C","D"].index(st.session_state.answers[st.session_state.current_q]),
                           key=f"user_q_{st.session_state.current_q}")
            if ans: st.session_state.answers[st.session_state.current_q] = ans

        c1, c2, c3 = st.columns([1,1,1])
        if c1.button("⬅️ Prev") and st.session_state.current_q > 0: st.session_state.current_q -= 1; st.rerun()
        if c2.button("Next ➡️") and st.session_state.current_q < len(qs)-1: st.session_state.current_q += 1; st.rerun()
        if c3.button("✅ Submit", type="primary"): st.session_state.submitted = True; st.rerun()

    elif st.session_state.get("submitted"):
        # Save Result Logic (Once)
        if not st.session_state.get("result_saved"):
            conn = get_connection(); cursor = conn.cursor()
            qs = cursor.execute("SELECT * FROM questions WHERE test_id=?", (st.session_state.test_id,)).fetchall()
            score = sum(1 for i, q in enumerate(qs) if st.session_state.answers.get(i) == q[8])
            cursor.execute("INSERT INTO results (name, department, test_id, score) VALUES (?, ?, ?, ?)",
                           (st.session_state.name, st.session_state.dept, st.session_state.test_id, score))
            conn.commit(); conn.close()
            st.session_state.result_saved = True
            st.session_state.final_score = score
            st.session_state.total_qs = len(qs)

        _, cent, _ = st.columns([1, 2, 1])
        with cent:
            st.balloons()
            st.markdown("<h2 style='text-align: center; color: #00D4FF !important;'>Assessment Completed</h2>", unsafe_allow_html=True)
            st.metric("Final Score", f"{st.session_state.final_score} / {st.session_state.total_qs}")
            if st.button("Exit Portal", use_container_width=True):
                st.session_state.clear(); st.rerun()
