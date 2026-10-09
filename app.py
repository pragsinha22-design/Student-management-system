"""
app.py  --  the Streamlit user interface (what the user sees and clicks).

How Streamlit works (important for your viva):
    * Streamlit runs this whole file from top to bottom EVERY time the user
      clicks a button or changes an input. This is called a "rerun".
    * st.session_state is a dictionary that survives reruns. We use it to
      remember the current page and to show one-time success messages.
    * This file never writes SQL. It calls functions from database.py, which
      read/write students.db. So:  Browser <-> app.py <-> database.py <-> SQLite

Run with:   python -m streamlit run app.py
"""

import re

import plotly.express as px
import streamlit as st

import database as db

# --------------------------------------------------------------------------
# Page setup (must be the FIRST Streamlit command)
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Student Management System",
    page_icon="🎓",
    layout="wide",
)

# Small bit of CSS for rounded dashboard cards and the blue theme.
CUSTOM_CSS = """
<style>
.block-container { padding-top: 2rem; max-width: 1200px; }
h1, h2, h3 { color: #0B3C7D; }
[data-testid="stSidebar"] { background: #F2F8FF; }
[data-testid="stMetric"] {
    background: #EAF4FF; border: 1px solid #CFE3F8;
    border-left: 6px solid #0B3C7D; border-radius: 14px; padding: 14px 18px;
}
[data-testid="stMetricValue"] { color: #0B3C7D; }
[data-testid="stForm"] { border: 1px solid #CFE3F8; border-radius: 14px; }
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    border-radius: 10px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Page names used by the sidebar menu and by the "quick action" buttons.
PAGE_DASHBOARD = "🏠 Dashboard"
PAGE_ADD = "➕ Add Student"
PAGE_VIEW = "📋 View Students"
PAGE_UPDATE = "✏️ Update Student"
PAGE_DELETE = "🗑️ Delete Student"
PAGES = [PAGE_DASHBOARD, PAGE_ADD, PAGE_VIEW, PAGE_UPDATE, PAGE_DELETE]

EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


# --------------------------------------------------------------------------
# Small helper functions (reused by several pages)
# --------------------------------------------------------------------------
def go_to(page):
    """Button callback: switch the sidebar menu to another page."""
    st.session_state["page"] = page


def flash(message):
    """Remember a success message so it can be shown after the next rerun."""
    st.session_state["flash"] = message


def show_flash():
    """Show (and remove) the remembered success message, if any."""
    message = st.session_state.pop("flash", None)
    if message:
        st.success(message)


def clean_text(value):
    """Trim spaces at both ends and collapse repeated spaces inside."""
    return " ".join((value or "").split())


def validate_student(name, roll_no, course, email, marks):
    """Check form input. Returns a list of error messages (empty = all OK)."""
    errors = []
    if not name:
        errors.append("Full name is required.")
    elif len(name) < 2:
        errors.append("Full name must be at least 2 characters.")
    if not roll_no:
        errors.append("Roll number is required.")
    if not course:
        errors.append("Course / department is required.")
    if not email:
        errors.append("Email address is required.")
    elif not EMAIL_PATTERN.match(email):
        errors.append("Please enter a valid email address (e.g. name@college.edu).")
    if marks is None:
        errors.append("Marks are required.")
    elif not (0 <= marks <= 100):
        errors.append("Marks must be between 0 and 100.")
    return errors


def display_table(df):
    """Rename database column names to friendly headings for display."""
    return df.rename(
        columns={
            "id": "ID",
            "name": "Name",
            "roll_no": "Roll No",
            "course": "Course",
            "email": "Email",
            "marks": "Marks",
        }
    )


MARKS_COLUMN = {"Marks": st.column_config.NumberColumn("Marks", format="%.1f")}


def student_label(student):
    """Text shown in the student dropdowns."""
    return f"{student['roll_no']} - {student['name']} ({student['course']})"


# --------------------------------------------------------------------------
# Page 1: Dashboard
# --------------------------------------------------------------------------
def render_dashboard():
    st.title("🎓 Student Management Dashboard")
    st.caption("All figures below are calculated live from the database.")
    show_flash()

    stats = db.get_statistics()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Total Students", stats["total"])
    col2.metric("📊 Average Marks", f"{stats['average']:.1f}")
    col3.metric("🏆 Highest Marks", f"{stats['highest']:.1f}")
    col4.metric("📚 Courses", stats["courses"])

    st.subheader("Quick actions")
    qa1, qa2, _ = st.columns([1, 1, 2])
    qa1.button("➕ Add a student", on_click=go_to, args=(PAGE_ADD,), key="qa_add")
    qa2.button("📋 View all students", on_click=go_to, args=(PAGE_VIEW,), key="qa_view")

    if stats["total"] == 0:
        st.info(
            "No student records yet. Click **Add a student** to register the "
            "first one - statistics and charts will appear here automatically."
        )
        return

    st.subheader("Average marks by course")
    course_df = db.get_average_marks_by_course()
    fig = px.bar(
        course_df,
        x="course",
        y="average_marks",
        labels={"course": "Course", "average_marks": "Average marks"},
        color_discrete_sequence=["#1F5FAF"],
    )
    fig.update_traces(texttemplate="%{y:.1f}", textposition="outside")
    fig.update_layout(
        yaxis_range=[0, 110],
        plot_bgcolor="white",
        margin=dict(t=20, l=10, r=10, b=10),
    )
    st.plotly_chart(fig)

    st.subheader("Recently added students")
    st.dataframe(
        display_table(db.get_recent_students(5)),
        hide_index=True,
        column_config=MARKS_COLUMN,
    )


# --------------------------------------------------------------------------
# Page 2: Add Student
# --------------------------------------------------------------------------
def render_add_student():
    st.title("➕ Add New Student")
    show_flash()

    # Changing the form id gives every widget a NEW key, which is how we
    # reset the form to empty after a successful save.
    form_id = st.session_state.setdefault("add_form_id", 0)

    existing = db.get_courses()
    if existing:
        st.caption("Existing courses: " + ", ".join(existing))

    with st.form(f"add_form_{form_id}"):
        name = st.text_input("Full name *", key=f"add_name_{form_id}")
        roll_no = st.text_input("Roll number * (must be unique)", key=f"add_roll_{form_id}")
        course = st.text_input("Course / department *", key=f"add_course_{form_id}")
        email = st.text_input("Email address *", key=f"add_email_{form_id}")
        marks = st.number_input(
            "Marks (out of 100) *",
            min_value=0.0,
            max_value=100.0,
            value=None,
            step=0.5,
            placeholder="Enter 0 - 100",
            key=f"add_marks_{form_id}",
        )
        submitted = st.form_submit_button("💾 Register student", type="primary")

    if submitted:
        name, roll_no = clean_text(name), clean_text(roll_no)
        course, email = clean_text(course), clean_text(email)

        errors = validate_student(name, roll_no, course, email, marks)
        if errors:
            for message in errors:
                st.error(message)
            return

        try:
            db.add_student(name, roll_no, course, email, marks)
        except db.DuplicateRollNumberError as error:
            st.error(str(error))
        except Exception:
            st.error("Something went wrong while saving. Please try again.")
        else:
            flash(f"✅ Student '{name}' was registered successfully.")
            st.session_state["add_form_id"] = form_id + 1  # reset the form
            st.rerun()


# --------------------------------------------------------------------------
# Page 3: View / Search students
# --------------------------------------------------------------------------
def render_view_students():
    st.title("📋 Student Records")
    show_flash()

    if db.get_statistics()["total"] == 0:
        st.info("No students registered yet. Use **Add Student** to create the first record.")
        st.button("➕ Add a student", on_click=go_to, args=(PAGE_ADD,), key="view_add")
        return

    col1, col2, col3 = st.columns([2, 1, 1])
    search = col1.text_input("🔍 Search by name or roll number", placeholder="e.g. Priya or CS101")
    course_choice = col2.selectbox("Course", ["All courses"] + db.get_courses())
    sort_by = col3.selectbox("Sort by", list(db.SORT_OPTIONS))

    course = None if course_choice == "All courses" else course_choice
    df = db.get_all_students(search=search, course=course, sort_by=sort_by)

    st.write(f"Showing **{len(df)}** student(s)")

    if df.empty:
        st.warning("No students match your search or filter. Try different keywords.")
        return

    st.dataframe(display_table(df), hide_index=True, column_config=MARKS_COLUMN)

    # utf-8-sig adds a marker so Excel on Windows opens the CSV correctly.
    csv_data = display_table(df).to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Download these records as CSV",
        data=csv_data,
        file_name="students.csv",
        mime="text/csv",
    )


# --------------------------------------------------------------------------
# Page 4: Update Student
# --------------------------------------------------------------------------
def render_update_student():
    st.title("✏️ Update Student")
    show_flash()

    df = db.get_all_students(sort_by="Name (A to Z)")
    if df.empty:
        st.info("There are no students to update yet.")
        return

    labels = {int(row["id"]): student_label(row) for _, row in df.iterrows()}
    student_id = st.selectbox(
        "Select a student to edit",
        list(labels),
        format_func=lambda sid: labels[sid],
        key="update_select",
    )

    student = db.get_student_by_id(student_id)
    if student is None:
        st.error("That student no longer exists. Please pick another one.")
        return

    # Keys include the student id, so choosing another student pre-fills the
    # form with THAT student's details.
    with st.form(f"update_form_{student_id}"):
        name = st.text_input("Full name *", value=student["name"], key=f"upd_name_{student_id}")
        roll_no = st.text_input("Roll number *", value=student["roll_no"], key=f"upd_roll_{student_id}")
        course = st.text_input("Course / department *", value=student["course"], key=f"upd_course_{student_id}")
        email = st.text_input("Email address *", value=student["email"], key=f"upd_email_{student_id}")
        marks = st.number_input(
            "Marks (out of 100) *",
            min_value=0.0,
            max_value=100.0,
            value=float(student["marks"]),
            step=0.5,
            key=f"upd_marks_{student_id}",
        )
        submitted = st.form_submit_button("💾 Save changes", type="primary")

    if submitted:
        name, roll_no = clean_text(name), clean_text(roll_no)
        course, email = clean_text(course), clean_text(email)

        errors = validate_student(name, roll_no, course, email, marks)
        if errors:
            for message in errors:
                st.error(message)
            return

        try:
            db.update_student(student_id, name, roll_no, course, email, marks)
        except db.DuplicateRollNumberError as error:
            st.error(str(error))
        except Exception:
            st.error("Something went wrong while saving. Please try again.")
        else:
            flash(f"✅ Details for '{name}' were updated successfully.")
            st.rerun()


# --------------------------------------------------------------------------
# Page 5: Delete Student
# --------------------------------------------------------------------------
def render_delete_student():
    st.title("🗑️ Delete Student")
    show_flash()

    df = db.get_all_students(sort_by="Name (A to Z)")
    if df.empty:
        st.info("There are no students to delete.")
        return

    labels = {int(row["id"]): student_label(row) for _, row in df.iterrows()}
    student_id = st.selectbox(
        "Select a student to delete",
        list(labels),
        format_func=lambda sid: labels[sid],
        key="delete_select",
    )

    student = db.get_student_by_id(student_id)
    if student is None:
        st.error("That student no longer exists. Please pick another one.")
        return

    st.warning("You are about to permanently delete this record:")
    with st.container(border=True):
        st.markdown(
            f"**ID:** {student['id']}  \n"
            f"**Name:** {student['name']}  \n"
            f"**Roll No:** {student['roll_no']}  \n"
            f"**Course:** {student['course']}  \n"
            f"**Email:** {student['email']}  \n"
            f"**Marks:** {student['marks']:.1f}"
        )

    # The delete button stays disabled until the box is ticked.
    confirmed = st.checkbox(
        "Yes, I am sure I want to delete this student.",
        key=f"delete_confirm_{student_id}",
    )
    if st.button("🗑️ Delete student", type="primary", disabled=not confirmed):
        try:
            deleted = db.delete_student(student_id)
        except Exception:
            st.error("Something went wrong while deleting. Please try again.")
            return
        if deleted:
            flash(f"✅ Student '{student['name']}' was deleted.")
        else:
            flash("That student had already been removed.")
        st.session_state.pop("delete_select", None)  # avoid a stale selection
        st.rerun()


# --------------------------------------------------------------------------
# Main: create the database, draw the sidebar, show the chosen page
# --------------------------------------------------------------------------
def main():
    db.init_db()  # creates students.db and the table on first run

    st.session_state.setdefault("page", PAGE_DASHBOARD)

    with st.sidebar:
        st.markdown("## 🎓 Student Admin")
        st.caption("Student Management System")
        st.radio("Navigation", PAGES, key="page", label_visibility="collapsed")
        st.divider()
        st.caption(f"Total students: **{db.get_statistics()['total']}**")

    page = st.session_state["page"]
    if page == PAGE_DASHBOARD:
        render_dashboard()
    elif page == PAGE_ADD:
        render_add_student()
    elif page == PAGE_VIEW:
        render_view_students()
    elif page == PAGE_UPDATE:
        render_update_student()
    elif page == PAGE_DELETE:
        render_delete_student()


main()
