"""
database.py  --  everything that talks to the SQLite database.

Why a separate file?
    Keeping all SQL here means app.py (the user interface) never contains SQL.
    If you change the database later, you only edit this file.

CRUD = Create, Read, Update, Delete.  Each one has a function below:
    Create -> add_student()
    Read   -> get_all_students(), get_student_by_id(), get_statistics(), ...
    Update -> update_student()
    Delete -> delete_student()

Security note:
    Every query uses "?" placeholders (parameterized queries). The values are
    passed separately from the SQL text, so a user typing  ' OR 1=1 --  into a
    form cannot change the meaning of the query (this prevents SQL injection).
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

# The database file lives next to this script, whatever folder you run from.
DB_PATH = Path(__file__).resolve().parent / "students.db"

# Allowed sort choices. The user picks a LABEL (left); we look up the SQL
# (right). Because the SQL comes from this fixed dictionary, never straight
# from user input, it is safe to place inside an ORDER BY clause.
SORT_OPTIONS = {
    "Newest first": "id DESC",
    "Name (A to Z)": "name COLLATE NOCASE ASC",
    "Name (Z to A)": "name COLLATE NOCASE DESC",
    "Marks (high to low)": "marks DESC, name COLLATE NOCASE ASC",
    "Marks (low to high)": "marks ASC, name COLLATE NOCASE ASC",
}


class DuplicateRollNumberError(Exception):
    """Raised when a roll number is already used by another student."""


# --------------------------------------------------------------------------
# Connection handling
# --------------------------------------------------------------------------
def get_connection():
    """Open a connection to students.db (the file is created if missing)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read columns by name: row["name"]
    return conn


@contextmanager
def db_connection():
    """
    Open a connection, then ALWAYS clean up:
      * no error  -> commit() saves the changes permanently
      * error     -> rollback() undoes the half-finished changes
      * finally   -> close() releases the file, even after an error
    Usage:  with db_connection() as conn:  conn.execute(...)
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create the students table if it does not exist (runs at app start)."""
    with db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL,
                roll_no TEXT NOT NULL UNIQUE COLLATE NOCASE,
                course  TEXT NOT NULL,
                email   TEXT NOT NULL,
                marks   REAL NOT NULL CHECK (marks >= 0 AND marks <= 100)
            )
            """
        )
        # COLLATE NOCASE makes "cs101" and "CS101" count as the SAME roll number.


# --------------------------------------------------------------------------
# CREATE
# --------------------------------------------------------------------------
def add_student(name, roll_no, course, email, marks):
    """Insert a new student and return the new row's id.
    Raises DuplicateRollNumberError if the roll number already exists."""
    try:
        with db_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO students (name, roll_no, course, email, marks) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, roll_no, course, email, float(marks)),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError as error:
        if "UNIQUE" in str(error).upper():
            raise DuplicateRollNumberError(
                f"Roll number '{roll_no}' is already registered."
            ) from error
        raise


# --------------------------------------------------------------------------
# READ
# --------------------------------------------------------------------------
def _escape_like(text):
    """Make % and _ typed by the user behave as normal characters in LIKE."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_all_students(search="", course=None, sort_by="Newest first"):
    """
    Return students as a pandas DataFrame, optionally filtered and sorted.
      search : text matched against name OR roll number (partial match)
      course : only students of this course (None = all courses)
      sort_by: one of the keys in SORT_OPTIONS
    """
    order_clause = SORT_OPTIONS.get(sort_by, SORT_OPTIONS["Newest first"])

    sql = "SELECT id, name, roll_no, course, email, marks FROM students WHERE 1=1"
    params = []

    search = (search or "").strip()
    if search:
        pattern = f"%{_escape_like(search)}%"
        sql += " AND (name LIKE ? ESCAPE '\\' OR roll_no LIKE ? ESCAPE '\\')"
        params += [pattern, pattern]

    if course:
        sql += " AND course = ? COLLATE NOCASE"
        params.append(course)

    sql += f" ORDER BY {order_clause}"  # safe: comes from SORT_OPTIONS only

    with db_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def get_student_by_id(student_id):
    """Return one student as a dict, or None if not found."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT id, name, roll_no, course, email, marks "
            "FROM students WHERE id = ?",
            (int(student_id),),
        ).fetchone()
    return dict(row) if row else None


def get_recent_students(limit=5):
    """Return the most recently added students (newest first)."""
    with db_connection() as conn:
        return pd.read_sql_query(
            "SELECT id, name, roll_no, course, email, marks "
            "FROM students ORDER BY id DESC LIMIT ?",
            conn,
            params=[int(limit)],
        )


def get_courses():
    """Return a sorted list of the distinct course names in the database."""
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT course FROM students "
            "GROUP BY course COLLATE NOCASE ORDER BY course COLLATE NOCASE"
        ).fetchall()
    return [row["course"] for row in rows]


def get_statistics():
    """Dashboard numbers, calculated by SQL aggregate functions."""
    with db_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*)                    AS total,
                   AVG(marks)                  AS average,
                   MAX(marks)                  AS highest,
                   COUNT(DISTINCT LOWER(course)) AS courses
            FROM students
            """
        ).fetchone()
    # AVG/MAX return NULL (None) on an empty table, so default to 0.
    return {
        "total": row["total"] or 0,
        "average": row["average"] or 0.0,
        "highest": row["highest"] or 0.0,
        "courses": row["courses"] or 0,
    }


def get_average_marks_by_course():
    """Average marks and student count per course (used for the bar chart)."""
    with db_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT course,
                   ROUND(AVG(marks), 2) AS average_marks,
                   COUNT(*)             AS students
            FROM students
            GROUP BY course COLLATE NOCASE
            ORDER BY average_marks DESC
            """,
            conn,
        )


# --------------------------------------------------------------------------
# UPDATE
# --------------------------------------------------------------------------
def update_student(student_id, name, roll_no, course, email, marks):
    """Change an existing student. Returns True if a row was updated.
    Raises DuplicateRollNumberError if the new roll number belongs to someone else."""
    try:
        with db_connection() as conn:
            cursor = conn.execute(
                "UPDATE students "
                "SET name = ?, roll_no = ?, course = ?, email = ?, marks = ? "
                "WHERE id = ?",
                (name, roll_no, course, email, float(marks), int(student_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.IntegrityError as error:
        if "UNIQUE" in str(error).upper():
            raise DuplicateRollNumberError(
                f"Roll number '{roll_no}' is already used by another student."
            ) from error
        raise


# --------------------------------------------------------------------------
# DELETE
# --------------------------------------------------------------------------
def delete_student(student_id):
    """Delete one student. Returns True if a row was removed."""
    with db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM students WHERE id = ?", (int(student_id),)
        )
        return cursor.rowcount > 0
