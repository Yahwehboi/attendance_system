import os
import sys
import zipfile
import io
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, send_from_directory,
                   jsonify, send_file)
from werkzeug.security import check_password_hash, generate_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_setup import setup_database, create_connection
from modules.registration import register_student, get_all_students, search_student
from modules.attendance import (mark_attendance_for_course,
                                get_attendance_by_course,
                                get_attendance_by_date,
                                get_all_attendance)
from modules.reports import export_to_excel, get_summary_report

def sanitize_input(text, max_length=100):
    """Basic input sanitization."""
    if not text:
        return ""
    # Remove dangerous characters
    text = str(text).strip()
    text = text[:max_length]
    return text

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "att_sys_secret_2024_!@#xyz")
app.config["SESSION_COOKIE_HTTPONLY"]  = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour timeout

# Rate limiter — prevents brute force attacks
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

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
@limiter.limit("10 per minute")
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Input validation
        if not username or not password:
            error = "Please enter username and password."
            return render_template("login.html", error=error)

        if len(username) > 50 or len(password) > 100:
            error = "Invalid input."
            return render_template("login.html", error=error)

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session.permanent = True
            session["user_id"]     = user[0]
            session["username"]    = user[1]
            session["full_name"]   = user[3]
            session["role"]        = user[5]
            session["last_active"] = datetime.now().timestamp()
            return redirect(url_for("dashboard"))
        error = "❌ Invalid username or password."
    return render_template("login.html", error=error)


@app.before_request
def check_session_timeout():
    """Auto logout after 1 hour of inactivity."""
    if request.endpoint in ('login', 'static', None):
        return
    if "user_id" in session:
        last_active = session.get("last_active")
        now = datetime.now().timestamp()
        if last_active and now - last_active > 3600:
            session.clear()
            flash("Session expired. Please login again.",
                  "error")
            return redirect(url_for("login"))
        session["last_active"] = now


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
        SELECT s.student_id, s.name,
               c.id, c.course_code, c.course_name
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
    departments = conn.execute(
        "SELECT DISTINCT department FROM students ORDER BY department"
    ).fetchall()
    levels = conn.execute(
        "SELECT DISTINCT level FROM students ORDER BY level"
    ).fetchall()
    conn.close()
    return render_template("admin/enrollments.html",
                           enrollments=enrollments,
                           students=students,
                           courses=courses,
                           departments=departments,
                           levels=levels)


@app.route("/admin/enrollments/batch_checkbox",
           methods=["POST"])
@login_required
@admin_required
def batch_enroll_checkbox():
    course_id   = request.form.get("course_id")
    student_ids = request.form.getlist("student_ids")

    if not course_id:
        flash("Please select a course.", "error")
        return redirect(url_for("manage_enrollments"))

    if not student_ids:
        flash("Please select at least one student.", "error")
        return redirect(url_for("manage_enrollments"))

    conn    = create_connection()
    success = 0
    for sid in student_ids:
        try:
            conn.execute('''
                INSERT OR IGNORE INTO enrollments
                (student_id, course_id) VALUES (?, ?)
            ''', (sid, course_id))
            success += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    flash(f"✅ {success} students enrolled successfully!",
          "success")
    return redirect(url_for("manage_enrollments"))


@app.route("/admin/enrollments/batch_dept",
           methods=["POST"])
@login_required
@admin_required
def batch_enroll_dept():
    course_id  = request.form.get("course_id")
    department = request.form.get("department", "").strip()
    level      = request.form.get("level", "").strip()

    if not course_id:
        flash("Please select a course.", "error")
        return redirect(url_for("manage_enrollments"))

    conn   = create_connection()
    query  = "SELECT student_id FROM students WHERE 1=1"
    params = []

    if department:
        query += " AND department=?"
        params.append(department)
    if level:
        query += " AND level=?"
        params.append(level)

    students = conn.execute(query, params).fetchall()

    if not students:
        flash("No students found with those filters.", "error")
        conn.close()
        return redirect(url_for("manage_enrollments"))

    success = 0
    for s in students:
        try:
            conn.execute('''
                INSERT OR IGNORE INTO enrollments
                (student_id, course_id) VALUES (?, ?)
            ''', (s[0], course_id))
            success += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    flash(
        f"✅ {success} students from "
        f"{department or 'all departments'} "
        f"Level {level or 'all levels'} enrolled!",
        "success")
    return redirect(url_for("manage_enrollments"))


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


@app.route("/api/get_students_for_course")
@login_required
@admin_required
def get_students_for_course():
    course_id = request.args.get("course_id")
    dept      = request.args.get("department", "")
    level     = request.args.get("level", "")

    conn   = create_connection()
    query  = '''
        SELECT s.student_id, s.name, s.department, s.level
        FROM students s
        WHERE s.student_id NOT IN (
            SELECT student_id FROM enrollments
            WHERE course_id = ?
        )
    '''
    params = [course_id]

    if dept:
        query += " AND s.department = ?"
        params.append(dept)
    if level:
        query += " AND s.level = ?"
        params.append(level)

    query += " ORDER BY s.name"
    students = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([{
        "student_id": s[0],
        "name":       s[1],
        "department": s[2],
        "level":      s[3]
    } for s in students])

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
    conn   = create_connection()
    course = conn.execute(
        "SELECT * FROM courses WHERE id=? AND user_id=?",
        (course_id, session["user_id"])).fetchone()
    if not course:
        return redirect(url_for("lecturer_dashboard"))

    date_filter = request.args.get(
        "date", datetime.now().strftime("%Y-%m-%d"))
    records  = get_attendance_by_course(course_id, date_filter)
    enrolled = conn.execute('''
        SELECT s.student_id, s.name, s.department, s.level
        FROM students s
        JOIN enrollments e ON s.student_id = e.student_id
        WHERE e.course_id = ?
        ORDER BY s.name
    ''', (course_id,)).fetchall()
    conn.close()
    return render_template("lecturer/attendance.html",
                           course=course,
                           records=records,
                           enrolled=enrolled,
                           date_filter=date_filter)
@app.route("/lecturer/manual_attendance/<int:course_id>",
           methods=["POST"])
@login_required
def manual_attendance(course_id):
    """Mark attendance manually by typing student ID."""
    conn   = create_connection()
    course = conn.execute(
        "SELECT * FROM courses WHERE id=? AND user_id=?",
        (course_id, session["user_id"])).fetchone()
    if not course:
        return redirect(url_for("lecturer_dashboard"))

    student_id = request.form.get("student_id", "").strip()
    if student_id:
        success, message = mark_attendance_for_course(
            student_id, course_id)
        flash(message, "success" if success else "error")
    else:
        flash("Please enter a student ID.", "error")

    conn.close()
    return redirect(url_for("lecturer_attendance",
                            course_id=course_id))

@app.route("/lecturer/reports/<int:course_id>")
@login_required
def lecturer_reports(course_id):
    conn   = create_connection()
    course = conn.execute(
        "SELECT * FROM courses WHERE id=? AND user_id=?",
        (course_id, session["user_id"])).fetchone()
    if not course:
        return redirect(url_for("lecturer_dashboard"))

    # Get total number of classes held for this course
    total_classes = conn.execute('''
        SELECT COUNT(DISTINCT date) FROM attendance
        WHERE course_id = ?
    ''', (course_id,)).fetchone()[0]

    summary = conn.execute('''
        SELECT s.student_id, s.name, s.department, s.level,
               COUNT(a.id) as total_present
        FROM students s
        JOIN enrollments e ON s.student_id = e.student_id
        LEFT JOIN attendance a ON s.student_id = a.student_id
                               AND a.course_id = ?
        WHERE e.course_id = ?
        GROUP BY s.student_id
        ORDER BY s.name
    ''', (course_id, course_id)).fetchall()
    conn.close()
    return render_template("lecturer/reports.html",
                           course=course,
                           summary=summary,
                           total_classes=total_classes)

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

    import zipfile
import io

@app.route("/admin/students/upload", methods=["POST"])
@login_required
@admin_required
def upload_students():
    """Bulk register students from Excel file."""
    if "file" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("manage_students"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("manage_students"))

    if not file.filename.endswith((".xlsx", ".xls")):
        flash("Please upload an Excel file (.xlsx or .xls)", "error")
        return redirect(url_for("manage_students"))

    try:
        import openpyxl
        wb = openpyxl.load_workbook(file)
        ws = wb.active

        success_count = 0
        error_count   = 0
        errors        = []

        # Skip header row, process each student
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]:
                continue

            try:
                student_id = str(row[0]).strip()
                name       = str(row[1]).strip()
                department = str(row[2]).strip() if row[2] else ""
                level      = str(row[3]).strip() if row[3] else ""
                email      = str(row[4]).strip() if row[4] else ""

                success, message = register_student(
                    student_id, name, department, level, email)

                if success:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"{student_id}: {message}")
            except Exception as e:
                error_count += 1
                errors.append(f"Row error: {str(e)}")

        msg = f"✅ {success_count} students registered successfully!"
        if error_count:
            msg += f" ⚠️ {error_count} failed: {', '.join(errors[:3])}"

        flash(msg, "success" if success_count > 0 else "error")

    except Exception as e:
        flash(f"❌ Error reading file: {str(e)}", "error")

    return redirect(url_for("manage_students"))


@app.route("/admin/students/download_qr_zip")
@login_required
@admin_required
def download_qr_zip():
    """Download all QR codes as a single ZIP file."""
    try:
        qr_dir   = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "qr_codes")
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w",
                             zipfile.ZIP_DEFLATED) as zip_file:
            for filename in os.listdir(qr_dir):
                if filename.endswith(".png"):
                    filepath = os.path.join(qr_dir, filename)
                    zip_file.write(filepath, filename)

        zip_buffer.seek(0)

        from flask import send_file
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="all_qr_codes.zip"
        )
    except Exception as e:
        flash(f"❌ Error creating zip: {str(e)}", "error")
        return redirect(url_for("manage_students"))


@app.route("/admin/students/download_qr/<sid>")
@login_required
@admin_required
def download_single_qr(sid):
    """Download a single student QR code."""
    qr_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "qr_codes")
    filename = f"{sid}.png"
    filepath = os.path.join(qr_dir, filename)

    if not os.path.exists(filepath):
        flash(f"❌ QR code not found for {sid}", "error")
        return redirect(url_for("manage_students"))

    from flask import send_file
    return send_file(
        filepath,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"QR_{sid}.png"
    )

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