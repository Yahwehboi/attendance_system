import os
import sys
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, send_from_directory,
                   jsonify)
from werkzeug.security import check_password_hash, generate_password_hash

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_setup import setup_database, create_connection
from modules.registration import register_student, get_all_students, search_student
from modules.attendance import (mark_attendance_for_course,
                                get_attendance_by_course,
                                get_attendance_by_date,
                                get_all_attendance)
from modules.reports import export_to_excel, get_summary_report

app = Flask(__name__)
app.secret_key = "attendance_secret_key_2024"

setup_database()

# ── AUTH DECORATORS ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("lecturer_dashboard"))
        return f(*args, **kwargs)
    return decorated

# ── AUTH ROUTES ───────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            session["user_id"]   = user[0]
            session["username"]  = user[1]
            session["full_name"] = user[3]
            session["role"]      = user[5]
            return redirect(url_for("dashboard"))
        error = "❌ Invalid username or password."
    return render_template("login.html", error=error)

@app.route("/dashboard")
@login_required
def dashboard():
    if session["role"] == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("lecturer_dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── ADMIN ROUTES ──────────────────────────────────────────────────────────────
@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    conn = create_connection()
    cursor = conn.cursor()
    total_students  = cursor.execute(
        "SELECT COUNT(*) FROM students").fetchone()[0]
    total_lecturers = cursor.execute(
        "SELECT COUNT(*) FROM users WHERE role='lecturer'").fetchone()[0]
    total_courses   = cursor.execute(
        "SELECT COUNT(*) FROM courses").fetchone()[0]
    today           = datetime.now().strftime("%Y-%m-%d")
    present_today   = cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE date=?",
        (today,)).fetchone()[0]
    recent = cursor.execute('''
        SELECT s.name, s.student_id, a.time, a.date
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        ORDER BY a.date DESC, a.time DESC LIMIT 10
    ''').fetchall()
    conn.close()
    return render_template("admin/dashboard.html",
                           total_students=total_students,
                           total_lecturers=total_lecturers,
                           total_courses=total_courses,
                           present_today=present_today,
                           recent=recent,
                           today=today)

# Students
@app.route("/admin/students", methods=["GET", "POST"])
@login_required
@admin_required
def manage_students():
    conn = create_connection()
    if request.method == "POST":
        sid       = request.form["student_id"].strip()
        name      = request.form["name"].strip()
        dept      = request.form["department"].strip()
        level     = request.form["level"].strip()
        email     = request.form["email"].strip()
        course_id = request.form.get("course_id", "").strip()
        success, message = register_student(sid, name, dept, level, email)
        if success and course_id:
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO enrollments (student_id, course_id)
                    VALUES (?, ?)
                ''', (sid, course_id))
                conn.commit()
            except Exception:
                pass
        flash(message, "success" if success else "error")

    search = request.args.get("search", "").strip()
    if search:
        students = search_student(search)
    else:
        students = get_all_students()

    courses = conn.execute("SELECT * FROM courses").fetchall()
    conn.close()
    return render_template("admin/students.html",
                           students=students,
                           courses=courses,
                           search=search)

@app.route("/admin/students/delete/<sid>")
@login_required
@admin_required
def delete_student(sid):
    conn = create_connection()
    conn.execute("DELETE FROM students WHERE student_id=?", (sid,))
    conn.commit()
    conn.close()
    flash("Student deleted successfully.", "success")
    return redirect(url_for("manage_students"))

# Lecturers
@app.route("/admin/lecturers", methods=["GET", "POST"])
@login_required
@admin_required
def manage_lecturers():
    conn = create_connection()
    if request.method == "POST":
        username  = request.form["username"].strip()
        full_name = request.form["full_name"].strip()
        email     = request.form["email"].strip()
        password  = request.form["password"].strip()
        try:
            conn.execute('''
                INSERT INTO users
                (username, password, full_name, email, role)
                VALUES (?, ?, ?, ?, 'lecturer')
            ''', (username,
                  generate_password_hash(password),
                  full_name, email))
            conn.commit()
            flash(f"Lecturer '{full_name}' added!", "success")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    lecturers = conn.execute(
        "SELECT * FROM users WHERE role='lecturer'"
    ).fetchall()
    conn.close()
    return render_template("admin/lecturers.html",
                           lecturers=lecturers)

@app.route("/admin/lecturers/delete/<int:lid>")
@login_required
@admin_required
def delete_lecturer(lid):
    conn = create_connection()
    conn.execute(
        "DELETE FROM users WHERE id=? AND role='lecturer'", (lid,))
    conn.commit()
    conn.close()
    flash("Lecturer deleted.", "success")
    return redirect(url_for("manage_lecturers"))

# Courses
@app.route("/admin/courses", methods=["GET", "POST"])
@login_required
@admin_required
def manage_courses():
    conn = create_connection()
    if request.method == "POST":
        code    = request.form["course_code"].strip().upper()
        name    = request.form["course_name"].strip()
        lect_id = request.form["lecturer_id"].strip()
        try:
            conn.execute('''
                INSERT INTO courses (course_code, course_name, user_id)
                VALUES (?, ?, ?)
            ''', (code, name, lect_id))
            conn.commit()
            flash(f"Course '{code}' created!", "success")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    courses = conn.execute('''
        SELECT c.id, c.course_code, c.course_name, u.full_name
        FROM courses c
        LEFT JOIN users u ON c.user_id = u.id
    ''').fetchall()
    lecturers = conn.execute(
        "SELECT * FROM users WHERE role='lecturer'"
    ).fetchall()
    conn.close()
    return render_template("admin/courses.html",
                           courses=courses,
                           lecturers=lecturers)

@app.route("/admin/courses/delete/<int:cid>")
@login_required
@admin_required
def delete_course(cid):
    conn = create_connection()
    conn.execute("DELETE FROM courses WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    flash("Course deleted.", "success")
    return redirect(url_for("manage_courses"))

# Enrollments
@app.route("/admin/enrollments", methods=["GET", "POST"])
@login_required
@admin_required
def manage_enrollments():
    conn = create_connection()
    if request.method == "POST":
        student_id = request.form["student_id"].strip()
        course_id  = request.form["course_id"].strip()
        try:
            conn.execute('''
                INSERT OR IGNORE INTO enrollments (student_id, course_id)
                VALUES (?, ?)
            ''', (student_id, course_id))
            conn.commit()
            flash("Student enrolled successfully!", "success")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    enrollments = conn.execute('''
        SELECT s.student_id, s.name, c.course_code, c.course_name
        FROM enrollments e
        JOIN students s ON e.student_id = s.student_id
        JOIN courses  c ON e.course_id  = c.id
        ORDER BY c.course_code, s.name
    ''').fetchall()
    students = conn.execute(
        "SELECT student_id, name FROM students"
    ).fetchall()
    courses = conn.execute(
        "SELECT id, course_code, course_name FROM courses"
    ).fetchall()
    conn.close()
    return render_template("admin/enrollments.html",
                           enrollments=enrollments,
                           students=students,
                           courses=courses)

@app.route("/admin/enrollments/delete/<sid>/<int:cid>")
@login_required
@admin_required
def delete_enrollment(sid, cid):
    conn = create_connection()
    conn.execute('''
        DELETE FROM enrollments
        WHERE student_id=? AND course_id=?
    ''', (sid, cid))
    conn.commit()
    conn.close()
    flash("Enrollment removed.", "success")
    return redirect(url_for("manage_enrollments"))

# ── LECTURER ROUTES ───────────────────────────────────────────────────────────
@app.route("/lecturer/dashboard")
@login_required
def lecturer_dashboard():
    conn = create_connection()
    today   = datetime.now().strftime("%Y-%m-%d")
    courses = conn.execute('''
        SELECT c.id, c.course_code, c.course_name,
               COUNT(DISTINCT e.student_id) as enrolled,
               COUNT(DISTINCT CASE WHEN a.date=? THEN a.id END) as present_today
        FROM courses c
        LEFT JOIN enrollments e ON c.id = e.course_id
        LEFT JOIN attendance  a ON c.id = a.course_id
        WHERE c.user_id = ?
        GROUP BY c.id
    ''', (today, session["user_id"])).fetchall()
    conn.close()
    return render_template("lecturer/dashboard.html",
                           courses=courses, today=today)

@app.route("/lecturer/attendance/<int:course_id>")
@login_required
def lecturer_attendance(course_id):
    conn    = create_connection()
    course  = conn.execute(
        "SELECT * FROM courses WHERE id=? AND user_id=?",
        (course_id, session["user_id"])).fetchone()
    if not course:
        return redirect(url_for("lecturer_dashboard"))

    date_filter = request.args.get(
        "date", datetime.now().strftime("%Y-%m-%d"))
    records = get_attendance_by_course(course_id, date_filter)
    enrolled = conn.execute('''
        SELECT s.student_id, s.name, s.department, s.level
        FROM students s
        JOIN enrollments e ON s.student_id = e.student_id
        WHERE e.course_id = ?
    ''', (course_id,)).fetchall()
    conn.close()
    return render_template("lecturer/attendance.html",
                           course=course,
                           records=records,
                           enrolled=enrolled,
                           date_filter=date_filter)

@app.route("/lecturer/reports/<int:course_id>")
@login_required
def lecturer_reports(course_id):
    conn   = create_connection()
    course = conn.execute(
        "SELECT * FROM courses WHERE id=? AND user_id=?",
        (course_id, session["user_id"])).fetchone()
    if not course:
        return redirect(url_for("lecturer_dashboard"))

    summary = conn.execute('''
        SELECT s.student_id, s.name, s.department, s.level,
               COUNT(a.id) as total_present
        FROM students s
        JOIN enrollments e ON s.student_id = e.student_id
        LEFT JOIN attendance a ON s.student_id = a.student_id
                               AND a.course_id = ?
        WHERE e.course_id = ?
        GROUP BY s.student_id
    ''', (course_id, course_id)).fetchall()
    conn.close()
    return render_template("lecturer/reports.html",
                           course=course, summary=summary)

@app.route("/lecturer/export/<int:course_id>")
@login_required
def export_course(course_id):
    success, message = export_to_excel(course_id=course_id)
    flash(message, "success" if success else "error")
    return redirect(url_for("lecturer_reports",
                            course_id=course_id))

# Mark attendance via API (called from scanner page)
@app.route("/api/mark", methods=["POST"])
@login_required
def api_mark():
    data       = request.get_json()
    student_id = data.get("student_id", "").strip()
    course_id  = data.get("course_id")
    if not student_id or not course_id:
        return jsonify({"success": False,
                        "message": "Missing data"})
    success, message = mark_attendance_for_course(
        student_id, course_id)
    return jsonify({"success": success, "message": message})

# Scanner page
@app.route("/lecturer/scan/<int:course_id>")
@login_required
def scan_page(course_id):
    conn   = create_connection()
    course = conn.execute(
        "SELECT * FROM courses WHERE id=? AND user_id=?",
        (course_id, session["user_id"])).fetchone()
    conn.close()
    if not course:
        return redirect(url_for("lecturer_dashboard"))
    return render_template("lecturer/scanner.html",
                           course=course)

# Serve QR code images
@app.route("/qr/<path:filename>")
def qr_image(filename):
    qr_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "qr_codes")
    return send_from_directory(qr_dir, filename)

# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Attendance Management System")
    print("  Open your browser and go to:")
    print("  http://localhost:5000")
    print("  or share with others on same WiFi:")
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"  http://{local_ip}:5000")
    print("="*50 + "\n")
    app.run(debug=False, host="0.0.0.0", port=5000)