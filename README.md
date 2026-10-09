# 🎓 Student Management System

A web application to register, search, update and delete student records, with a live dashboard.
Built with **Python, Streamlit, SQLite and Pandas** as a college project.

## 1. Introduction

The Student Management System lets a college administrator manage student records from a browser.
All data is stored permanently in a SQLite file (`students.db`), so records are still there after
the app is closed and restarted. No database server or manual setup is needed.

## 2. Objectives

- Build a complete CRUD (Create, Read, Update, Delete) application.
- Store data permanently using a relational database.
- Validate user input and handle errors gracefully.
- Present live statistics and charts calculated from real data.
- Practise clean, modular, well-commented Python code.

## 3. Features

- **Dashboard:** total students, average marks, highest marks, number of courses, bar chart of
  average marks by course, recent records table, quick-action buttons.
- **Add student:** validation of required fields, email format, marks 0-100, unique roll number.
- **View students:** search by name or roll number, filter by course, sort by name or marks,
  CSV download.
- **Update student:** pick a student, form is pre-filled, all fields validated.
- **Delete student:** shows details first and needs an explicit confirmation tick.
- Friendly success messages, error messages and empty-state messages.
- Responsive layout (columns stack on small screens), white / light-blue / dark-blue theme.

## 4. Technology Stack

| Purpose | Technology |
|---|---|
| Language | Python 3.9+ |
| Web framework | Streamlit |
| Database | SQLite (built into Python) |
| Data processing | Pandas |
| Charts | Plotly |

## 5. Project Folder Structure

```
student_management_system/
├── app.py               # Streamlit interface: sidebar, dashboard and all pages
├── database.py          # Database connection + CRUD functions (all SQL lives here)
├── test_database.py     # Automatic tests for the database functions
├── requirements.txt     # Python libraries to install
├── README.md            # This file
├── .streamlit/
│   └── config.toml      # Colour theme (white / light blue / dark blue)
└── students.db          # Created automatically the first time you run the app
```

**Purpose of each file**

- `app.py` - everything the user sees. It contains one function per page and calls `database.py`.
- `database.py` - creates the table and provides `add_student`, `get_all_students`,
  `update_student`, `delete_student` and helper query functions.
- `requirements.txt` - lets `pip` install the exact libraries needed.
- `test_database.py` - checks that the database logic works.
- `.streamlit/config.toml` - sets the colours.

## 6. Installation (Windows + VS Code)

1. Install Python from https://www.python.org/downloads/ (tick **"Add Python to PATH"** in the installer).
2. Open the `student_management_system` folder in VS Code (**File > Open Folder**).
3. Open the terminal in VS Code (**Terminal > New Terminal**) and check Python:

```powershell
python --version
```

4. (Recommended) Create and activate a virtual environment:

```powershell
python -m venv venv
venv\Scripts\activate
```

If PowerShell says scripts are disabled, run this once and try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

5. Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## 7. Running the Application

Make sure the terminal is inside the project folder, then run:

```powershell
python -m streamlit run app.py
```

Your browser opens at `http://localhost:8501`. Press `Ctrl + C` in the terminal to stop the app.
`students.db` appears in the folder after the first launch.

## 8. The Database

- File: `students.db` (SQLite). It is created automatically by `init_db()` when the app starts.
- Table: `students`

| Column | Type | Rules |
|---|---|---|
| `id` | INTEGER | Primary key, auto-increment |
| `name` | TEXT | Required |
| `roll_no` | TEXT | Required, **unique** (case-insensitive) |
| `course` | TEXT | Required |
| `email` | TEXT | Required |
| `marks` | REAL | Required, `CHECK` between 0 and 100 |

Key design points:

- **Parameterized queries** (`?` placeholders) prevent SQL injection.
- **Transactions:** the `db_connection()` helper commits on success, rolls back on error,
  and always closes the connection.
- **UNIQUE constraint:** the database itself refuses duplicate roll numbers; `database.py` turns
  that into a friendly `DuplicateRollNumberError`.

## 9. CRUD Operations (useful for your viva)

CRUD stands for the four basic operations on stored data.

| Operation | Meaning | Function in `database.py` | SQL used |
|---|---|---|---|
| **Create** | Add a new record | `add_student()` | `INSERT INTO students (...) VALUES (?, ?, ?, ?, ?)` |
| **Read** | Fetch records | `get_all_students()`, `get_student_by_id()` | `SELECT ... FROM students WHERE ... ORDER BY ...` |
| **Update** | Change a record | `update_student()` | `UPDATE students SET ... WHERE id = ?` |
| **Delete** | Remove a record | `delete_student()` | `DELETE FROM students WHERE id = ?` |

Important SQL used in the project:

- `COUNT(*)`, `AVG(marks)`, `MAX(marks)` - aggregate functions for dashboard cards.
- `GROUP BY course` - groups rows by course so `AVG(marks)` is calculated per course (bar chart).
- `LIKE '%text%'` - partial-text search on name and roll number.
- `ORDER BY` - sorting (the allowed options come from a fixed dictionary, never from user text).
- `WHERE id = ?` - makes sure update and delete affect exactly one student.

### How Streamlit interacts with SQLite

1. The user clicks something in the browser (for example **Register student**).
2. Streamlit re-runs `app.py` from top to bottom (a "rerun").
3. `app.py` validates the input and calls a function such as `db.add_student(...)`.
4. `database.py` opens `students.db`, runs the SQL with parameters, commits and closes.
5. `app.py` reads fresh data with `db.get_statistics()` etc. and redraws the page.

`st.session_state` is a dictionary that survives reruns. It stores the current page and one-time
success messages.

## 10. Testing

### Automatic tests

```powershell
python -m unittest test_database -v
```

All tests should show `ok`. They use a temporary database, so your real data is not touched.

### Manual test checklist

1. **Empty state:** delete `students.db`, launch the app. The dashboard shows zeros and a helpful message.
2. **Add:** register 3-4 students in at least two courses. A success message appears and the form clears.
3. **Validation:** try empty fields, an email like `abc`, and (if you can) marks above 100. Errors appear.
4. **Duplicate:** add a student with an existing roll number. A clear error appears (also for `cs101` vs `CS101`).
5. **Dashboard:** totals, average, highest, course count and the bar chart match your data.
6. **Search / filter / sort:** search by part of a name or roll number, filter by course, sort by marks.
   A search like `zzz` shows "No students match".
7. **CSV:** click **Download these records as CSV** and open the file in Excel.
8. **Update:** change a student's marks, then check the dashboard and records page.
9. **Delete:** the button stays disabled until the checkbox is ticked. After deleting, the record is gone.
10. **Persistence:** stop the app (`Ctrl + C`), start it again. The records are still there.

## 11. Possible Future Improvements

- Login system with admin and teacher roles.
- Extra fields: date of birth, phone number, attendance, grade, photo.
- Per-subject marks and automatic grade calculation.
- Import students from a CSV or Excel file.
- Pagination for very large tables.
- PDF report cards.
- Move to a server database such as PostgreSQL or MySQL for multi-user deployment.

## 12. Short Viva Notes

- **What is Streamlit?** A Python library that turns scripts into web apps without HTML/JavaScript.
- **Why SQLite?** It needs no server, stores everything in one file and is built into Python.
- **What is a primary key?** A column (`id`) that uniquely identifies each row.
- **What is SQL injection?** An attack where user text changes the meaning of a query. We prevent it
  with parameterized queries (`?`).
- **What is a transaction?** A group of changes that is saved together (`commit`) or undone together
  (`rollback`).
- **Why separate `app.py` and `database.py`?** Separation of concerns: the interface and the data
  logic can be changed independently and are easier to understand and test.
- **What is Pandas used for?** Holding query results as a DataFrame for tables, charts and CSV export.
