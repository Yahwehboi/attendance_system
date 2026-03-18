import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash

# ── Path setup ────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(APP_DIR, "attendance.db")


def create_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn


def setup_database():
    conn = create_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email     TEXT,
            role      TEXT DEFAULT 'lecturer'
        )
    ''')

    # Courses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT UNIQUE NOT NULL,
            course_name TEXT NOT NULL,
            user_id     INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id   TEXT UNIQUE NOT NULL,
            name         TEXT NOT NULL,
            department   TEXT,
            level        TEXT,
            email        TEXT,
            qr_code_path TEXT
        )
    ''')

    # Enrollments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            course_id  INTEGER NOT NULL,
            UNIQUE(student_id, course_id),
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (course_id)  REFERENCES courses(id)
        )
    ''')

    # Attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            course_id  INTEGER,
            date       TEXT NOT NULL,
            time       TEXT NOT NULL,
            status     TEXT DEFAULT 'Present',
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (course_id)  REFERENCES courses(id)
        )
    ''')

    # Default admin
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, full_name, email, role)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin',
              generate_password_hash('admin123'),
              'System Administrator',
              'admin@system.com',
              'admin'))
        print("✅ Default admin created → username: admin | password: admin123")

    conn.commit()
    conn.close()
    print("✅ Database setup complete.")


if __name__ == "__main__":
    setup_database()