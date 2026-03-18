import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_setup import create_connection
from modules.qr_generator import generate_qr_code

def register_student(student_id, name, department, level, email):
    """Register a new student and generate their QR code."""

    conn = create_connection()
    cursor = conn.cursor()

    # Check if student already exists
    cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    if cursor.fetchone():
        conn.close()
        return False, f"❌ Student ID '{student_id}' already exists."

    # Generate QR code first
    qr_path = generate_qr_code(student_id, name)

    # Save student to database
    cursor.execute('''
        INSERT INTO students (student_id, name, department, level, email, qr_code_path)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (student_id, name, department, level, email, qr_path))

    conn.commit()
    conn.close()

    return True, f"✅ Student '{name}' registered successfully!"

def get_all_students():
    """Fetch all registered students."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name, department, level, email FROM students")
    students = cursor.fetchall()
    conn.close()
    return students

def search_student(keyword):
    """Search student by ID or name."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT student_id, name, department, level, email 
        FROM students
        WHERE student_id LIKE ? OR name LIKE ?
    ''', (f"%{keyword}%", f"%{keyword}%"))
    results = cursor.fetchall()
    conn.close()
    return results