"""
test_database.py  --  automatic tests for the CRUD functions.

Run with:  python -m unittest test_database -v
The tests use a temporary database file, so your real students.db is untouched.
"""

import tempfile
import unittest
from pathlib import Path

import database as db


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        # Point the database module at a fresh temporary file for each test.
        self.tmp = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self.tmp.name) / "test_students.db"
        db.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_statistics(self):
        stats = db.get_statistics()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["average"], 0)

    def test_add_and_read(self):
        sid = db.add_student("Asha Rao", "CS101", "Computer Science", "asha@x.edu", 88)
        student = db.get_student_by_id(sid)
        self.assertEqual(student["name"], "Asha Rao")
        self.assertEqual(student["marks"], 88)

    def test_duplicate_roll_number_rejected(self):
        db.add_student("A", "CS101", "CS", "a@x.edu", 50)
        with self.assertRaises(db.DuplicateRollNumberError):
            db.add_student("B", "cs101", "CS", "b@x.edu", 60)  # different case

    def test_marks_range_enforced_by_database(self):
        with self.assertRaises(Exception):
            db.add_student("A", "R1", "CS", "a@x.edu", 150)

    def test_statistics_and_course_average(self):
        db.add_student("A", "R1", "CS", "a@x.edu", 80)
        db.add_student("B", "R2", "CS", "b@x.edu", 60)
        db.add_student("C", "R3", "IT", "c@x.edu", 90)
        stats = db.get_statistics()
        self.assertEqual(stats["total"], 3)
        self.assertAlmostEqual(stats["average"], 76.6667, places=3)
        self.assertEqual(stats["highest"], 90)
        self.assertEqual(stats["courses"], 2)
        avg = db.get_average_marks_by_course().set_index("course")["average_marks"]
        self.assertEqual(avg["CS"], 70)

    def test_search_filter_sort(self):
        db.add_student("Priya Shah", "CS101", "CS", "p@x.edu", 70)
        db.add_student("Rahul Mehta", "IT202", "IT", "r@x.edu", 95)
        self.assertEqual(len(db.get_all_students(search="priya")), 1)
        self.assertEqual(len(db.get_all_students(search="it202")), 1)
        self.assertEqual(len(db.get_all_students(course="IT")), 1)
        self.assertEqual(len(db.get_all_students(search="zzz")), 0)
        top = db.get_all_students(sort_by="Marks (high to low)").iloc[0]
        self.assertEqual(top["name"], "Rahul Mehta")

    def test_sql_injection_text_is_harmless(self):
        db.add_student("A", "R1", "CS", "a@x.edu", 50)
        self.assertEqual(len(db.get_all_students(search="' OR 1=1 --")), 0)

    def test_update(self):
        sid = db.add_student("A", "R1", "CS", "a@x.edu", 50)
        other = db.add_student("B", "R2", "CS", "b@x.edu", 60)
        self.assertTrue(db.update_student(sid, "A New", "R1", "IT", "a@x.edu", 75))
        self.assertEqual(db.get_student_by_id(sid)["marks"], 75)
        with self.assertRaises(db.DuplicateRollNumberError):
            db.update_student(other, "B", "R1", "CS", "b@x.edu", 60)

    def test_delete(self):
        sid = db.add_student("A", "R1", "CS", "a@x.edu", 50)
        self.assertTrue(db.delete_student(sid))
        self.assertIsNone(db.get_student_by_id(sid))
        self.assertFalse(db.delete_student(sid))


if __name__ == "__main__":
    unittest.main()
