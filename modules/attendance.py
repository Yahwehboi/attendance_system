import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_setup import create_connection

def mark_attendance_for_course(student_id, course_id):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM students WHERE student_id=?", (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return False, f"❌ Student '{student_id}' not found."

    name = student[0]
    date = datetime.now().strftime("%Y-%m-%d")
    time = datetime.now().strftime("%H:%M:%S")

    # Check enrollment
    cursor.execute('''
        SELECT * FROM enrollments
        WHERE student_id=? AND course_id=?
    ''', (student_id, course_id))
    if not cursor.fetchone():
        conn.close()
        return False, f"⚠️ '{name}' not enrolled in this course."

    # Prevent duplicate
    cursor.execute('''
        SELECT * FROM attendance
        WHERE student_id=? AND course_id=? AND date=?
    ''', (student_id, course_id, date))
    if cursor.fetchone():
        conn.close()
        return False, f"⚠️ '{name}' already marked present today."

    cursor.execute('''
        INSERT INTO attendance (student_id, course_id, date, time, status)
        VALUES (?, ?, ?, ?, 'Present')
    ''', (student_id, course_id, date, time))

    conn.commit()
    conn.close()
    return True, f"✅ Attendance marked for '{name}' at {time}"

def mark_attendance(student_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM students WHERE student_id=?", (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return False, f"❌ Student '{student_id}' not found."
    name = student[0]
    date = datetime.now().strftime("%Y-%m-%d")
    time = datetime.now().strftime("%H:%M:%S")
    cursor.execute('''
        SELECT * FROM attendance WHERE student_id=? AND date=?
    ''', (student_id, date))
    if cursor.fetchone():
        conn.close()
        return False, f"⚠️ '{name}' already marked present today."
    cursor.execute('''
        INSERT INTO attendance (student_id, date, time, status)
        VALUES (?, ?, ?, 'Present')
    ''', (student_id, date, time))
    conn.commit()
    conn.close()
    return True, f"✅ Attendance marked for '{name}' at {time}"

def get_attendance_by_course(course_id, date=None):
    conn = create_connection()
    cursor = conn.cursor()
    if date:
        cursor.execute('''
            SELECT s.student_id, s.name, s.department,
                   s.level, a.date, a.time, a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.course_id=? AND a.date=?
            ORDER BY a.time ASC
        ''', (course_id, date))
    else:
        cursor.execute('''
            SELECT s.student_id, s.name, s.department,
                   s.level, a.date, a.time, a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.course_id=?
            ORDER BY a.date DESC, a.time ASC
        ''', (course_id,))
    records = cursor.fetchall()
    conn.close()
    return records

def get_attendance_by_date(date=None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.student_id, s.name, s.department, s.level,
               a.date, a.time, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.date=?
        ORDER BY a.time ASC
    ''', (date,))
    records = cursor.fetchall()
    conn.close()
    return records

def get_all_attendance():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.student_id, s.name, s.department, s.level,
               a.date, a.time, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        ORDER BY a.date DESC, a.time ASC
    ''')
    records = cursor.fetchall()
    conn.close()
    return records

def get_student_attendance_summary():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.student_id, s.name, s.department, s.level,
               COUNT(a.id) as total_present
        FROM students s
        LEFT JOIN attendance a ON s.student_id = a.student_id
        GROUP BY s.student_id
        ORDER BY s.name ASC
    ''')
    records = cursor.fetchall()
    conn.close()
    return records