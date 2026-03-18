import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

# ── Path setup ────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(BASE_DIR)

from database.db_setup import setup_database, create_connection
from modules.registration import register_student, get_all_students, search_student
from modules.attendance import (get_attendance_by_date, get_all_attendance,
                                get_attendance_by_course)
from modules.reports import export_to_excel, get_summary_report
from modules.qr_scanner import start_scanner

# ── COLORS ────────────────────────────────────────────────────────────────────
BG_DARK      = "#1e1e2e"
BG_SIDEBAR   = "#181825"
BG_CARD      = "#2a2a3e"
ACCENT       = "#7c3aed"
ACCENT_HOVER = "#6d28d9"
TEXT_PRIMARY = "#cdd6f4"
TEXT_MUTED   = "#6c7086"
SUCCESS      = "#a6e3a1"
WARNING      = "#f9e2af"
ERROR        = "#f38ba8"
WHITE        = "#ffffff"


# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Attendance System — Login")
        self.root.geometry("420x520")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(False, False)
        self.center_window(420, 520)
        self.build()

    def center_window(self, w, h):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw // 2) - (w // 2)
        y  = (sh // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def build(self):
        # Header
        header = tk.Frame(self.root, bg=ACCENT, pady=30)
        header.pack(fill="x")
        tk.Label(header, text="🎓",
                 font=("Segoe UI", 36),
                 bg=ACCENT, fg=WHITE).pack()
        tk.Label(header, text="Attendance Management System",
                 font=("Segoe UI", 13, "bold"),
                 bg=ACCENT, fg=WHITE).pack()
        tk.Label(header, text="Sign in to continue",
                 font=("Segoe UI", 9),
                 bg=ACCENT, fg="#e9d5ff").pack()

        # Form
        form = tk.Frame(self.root, bg=BG_DARK, padx=40, pady=30)
        form.pack(fill="both", expand=True)

        tk.Label(form, text="Username",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(anchor="w")
        self.username_entry = tk.Entry(
            form, font=("Segoe UI", 12),
            bg=BG_CARD, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat", bd=8)
        self.username_entry.pack(fill="x", pady=(4, 16))

        tk.Label(form, text="Password",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(anchor="w")
        self.password_entry = tk.Entry(
            form, font=("Segoe UI", 12),
            bg=BG_CARD, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat", bd=8, show="•")
        self.password_entry.pack(fill="x", pady=(4, 20))

        self.error_label = tk.Label(
            form, text="",
            font=("Segoe UI", 10),
            bg=BG_DARK, fg=ERROR)
        self.error_label.pack()

        tk.Button(
            form, text="Login",
            font=("Segoe UI", 12, "bold"),
            bg=ACCENT, fg=WHITE,
            activebackground=ACCENT_HOVER,
            relief="flat", pady=10,
            cursor="hand2",
            command=self.do_login).pack(fill="x", pady=10)

        tk.Label(form,
                 text="Default admin: username=admin | password=admin123",
                 font=("Segoe UI", 8),
                 bg=BG_DARK, fg=TEXT_MUTED).pack()

        self.root.bind("<Return>", lambda e: self.do_login())

    def do_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            self.error_label.config(
                text="❌ Please enter username and password.")
            return

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            self.root.destroy()
            root = tk.Tk()
            MainApp(root, user)
            root.mainloop()
        else:
            self.error_label.config(
                text="❌ Invalid username or password.")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════
class MainApp:
    def __init__(self, root, user):
        self.root      = root
        self.user      = user
        self.user_id   = user[0]
        self.username  = user[1]
        self.full_name = user[3]
        self.role      = user[5]

        self.root.title(
            f"Attendance System — {self.full_name} ({self.role.title()})")
        self.root.geometry("1100x680")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(True, True)
        self.setup_styles()
        self.build_layout()
        self.show_dashboard()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=BG_CARD,
                        foreground=TEXT_PRIMARY,
                        fieldbackground=BG_CARD,
                        rowheight=30,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background=ACCENT,
                        foreground=WHITE,
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", WHITE)])

    def build_layout(self):
        self.sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.content = tk.Frame(self.root, bg=BG_DARK)
        self.content.pack(side="left", fill="both", expand=True)
        self.build_sidebar()

    def build_sidebar(self):
        # Title
        title_frame = tk.Frame(self.sidebar, bg=ACCENT, pady=20)
        title_frame.pack(fill="x")
        tk.Label(title_frame, text="🎓",
                 font=("Segoe UI", 28),
                 bg=ACCENT, fg=WHITE).pack()
        tk.Label(title_frame, text="Attendance System",
                 font=("Segoe UI", 11, "bold"),
                 bg=ACCENT, fg=WHITE).pack()
        tk.Label(title_frame,
                 text=f"{self.full_name}\n({self.role.title()})",
                 font=("Segoe UI", 8),
                 bg=ACCENT, fg="#e9d5ff").pack()

        tk.Frame(self.sidebar, bg=BG_SIDEBAR, height=10).pack()

        # Nav items based on role
        if self.role == "admin":
            nav_items = [
                ("🏠  Dashboard",        self.show_dashboard),
                ("📋  Register Student", self.show_registration),
                ("📷  Scan QR Code",     self.show_scanner),
                ("📅  Attendance",       self.show_attendance),
                ("📊  Reports",          self.show_reports),
                ("👥  All Students",     self.show_students),
                ("👨‍🏫  Lecturers",        self.show_lecturers),
                ("📚  Courses",          self.show_courses),
                ("🔗  Enroll Students",  self.show_enrollments),
            ]
        else:
            nav_items = [
                ("🏠  My Dashboard",    self.show_dashboard),
                ("📷  Scan Attendance", self.show_scanner),
                ("📅  Attendance",      self.show_attendance),
                ("📊  Reports",         self.show_reports),
            ]

        self.nav_buttons = []
        for label, command in nav_items:
            btn = tk.Button(
                self.sidebar, text=label,
                font=("Segoe UI", 10),
                bg=BG_SIDEBAR, fg=TEXT_PRIMARY,
                activebackground=ACCENT,
                activeforeground=WHITE,
                bd=0, pady=13, padx=20,
                anchor="w", cursor="hand2",
                command=lambda c=command,
                b=label: self.nav_click(c, b))
            btn.pack(fill="x")
            self.nav_buttons.append(btn)

        tk.Frame(self.sidebar, bg=BG_SIDEBAR).pack(
            fill="y", expand=True)

        # Logout
        tk.Button(self.sidebar, text="🚪  Logout",
                  font=("Segoe UI", 10),
                  bg=BG_SIDEBAR, fg=ERROR,
                  activebackground="#3d1a1a",
                  bd=0, pady=13, padx=20,
                  anchor="w", cursor="hand2",
                  command=self.logout).pack(fill="x")
        tk.Label(self.sidebar,
                 text="v2.0  •  Final Year Project",
                 font=("Segoe UI", 8),
                 bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(pady=6)

    def logout(self):
        if messagebox.askyesno("Logout",
                               "Are you sure you want to logout?"):
            self.root.destroy()
            root = tk.Tk()
            LoginWindow(root)
            root.mainloop()

    def nav_click(self, command, label):
        for btn in self.nav_buttons:
            btn.configure(bg=BG_SIDEBAR, fg=TEXT_PRIMARY)
            if btn["text"] == label:
                btn.configure(bg=ACCENT, fg=WHITE)
        command()

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def page_header(self, title, subtitle=""):
        header = tk.Frame(self.content, bg=BG_DARK,
                          pady=20, padx=30)
        header.pack(fill="x")
        tk.Label(header, text=title,
                 font=("Segoe UI", 22, "bold"),
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(anchor="w")
        if subtitle:
            tk.Label(header, text=subtitle,
                     font=("Segoe UI", 10),
                     bg=BG_DARK, fg=TEXT_MUTED).pack(anchor="w")
        tk.Frame(self.content, bg=ACCENT,
                 height=2).pack(fill="x", padx=30)

    # ── DASHBOARD ─────────────────────────────────────────────────
    def show_dashboard(self):
        self.clear_content()
        self.page_header(
            "Dashboard",
            f"Welcome, {self.full_name}  •  "
            f"{datetime.now().strftime('%A, %d %B %Y')}")

        cards_frame = tk.Frame(self.content, bg=BG_DARK,
                               pady=20, padx=30)
        cards_frame.pack(fill="x")

        if self.role == "admin":
            conn = create_connection()
            cursor = conn.cursor()
            total_students  = len(get_all_students())
            today           = datetime.now().strftime("%Y-%m-%d")
            present_today   = len(get_attendance_by_date(today))
            total_courses   = cursor.execute(
                "SELECT COUNT(*) FROM courses"
            ).fetchone()[0]
            total_lecturers = cursor.execute(
                "SELECT COUNT(*) FROM users WHERE role='lecturer'"
            ).fetchone()[0]
            conn.close()

            stats = [
                ("👥 Total Students",  total_students,  ACCENT),
                ("✅ Present Today",   present_today,   "#059669"),
                ("📚 Total Courses",   total_courses,   "#0891b2"),
                ("👨‍🏫 Lecturers",       total_lecturers, "#d97706"),
            ]
            for i, (label, value, color) in enumerate(stats):
                card = tk.Frame(cards_frame, bg=BG_CARD,
                                padx=20, pady=20)
                card.grid(row=0, column=i, padx=10, sticky="ew")
                cards_frame.columnconfigure(i, weight=1)
                tk.Label(card, text=str(value),
                         font=("Segoe UI", 28, "bold"),
                         bg=BG_CARD, fg=color).pack()
                tk.Label(card, text=label,
                         font=("Segoe UI", 10),
                         bg=BG_CARD, fg=TEXT_MUTED).pack()

            # Today's attendance table
            section = tk.Frame(self.content, bg=BG_DARK, padx=30)
            section.pack(fill="both", expand=True, pady=10)
            tk.Label(section, text="Today's Attendance",
                     font=("Segoe UI", 13, "bold"),
                     bg=BG_DARK, fg=TEXT_PRIMARY).pack(
                         anchor="w", pady=(0, 8))
            self.build_table(
                section,
                ["Student ID", "Name", "Department",
                 "Level", "Date", "Time", "Status"],
                get_attendance_by_date())

        else:
            # Lecturer dashboard — show their courses
            conn = create_connection()
            cursor = conn.cursor()
            courses = cursor.execute('''
                SELECT c.id, c.course_code, c.course_name,
                       COUNT(e.id) as enrolled
                FROM courses c
                LEFT JOIN enrollments e ON c.id = e.course_id
                WHERE c.user_id = ?
                GROUP BY c.id
            ''', (self.user_id,)).fetchall()
            conn.close()

            tk.Label(cards_frame, text="Your Courses",
                     font=("Segoe UI", 13, "bold"),
                     bg=BG_DARK, fg=TEXT_PRIMARY).grid(
                         row=0, column=0, columnspan=4,
                         sticky="w", pady=(0, 10))

            if not courses:
                tk.Label(cards_frame,
                         text="No courses assigned yet. "
                              "Contact admin.",
                         font=("Segoe UI", 11),
                         bg=BG_DARK, fg=TEXT_MUTED).grid(
                             row=1, column=0)
                return

            for i, course in enumerate(courses):
                card = tk.Frame(cards_frame, bg=BG_CARD,
                                padx=20, pady=20)
                card.grid(row=1, column=i, padx=10, sticky="ew")
                cards_frame.columnconfigure(i, weight=1)
                tk.Label(card, text=course[1],
                         font=("Segoe UI", 16, "bold"),
                         bg=BG_CARD, fg=ACCENT).pack()
                tk.Label(card, text=course[2],
                         font=("Segoe UI", 10),
                         bg=BG_CARD, fg=TEXT_PRIMARY).pack()
                tk.Label(card,
                         text=f"{course[3]} students enrolled",
                         font=("Segoe UI", 9),
                         bg=BG_CARD, fg=TEXT_MUTED).pack(pady=4)
                tk.Button(card, text="📷 Scan Now",
                          font=("Segoe UI", 9, "bold"),
                          bg=ACCENT, fg=WHITE,
                          relief="flat", padx=10, pady=4,
                          cursor="hand2",
                          command=lambda cid=course[0]:
                          self.scan_for_course(cid)).pack(pady=4)

    # ── SCANNER ───────────────────────────────────────────────────
    def show_scanner(self):
        self.clear_content()
        self.page_header("QR Code Scanner",
                         "Scan QR codes to mark attendance")

        if self.role == "lecturer":
            conn = create_connection()
            cursor = conn.cursor()
            courses = cursor.execute('''
                SELECT id, course_code, course_name
                FROM courses WHERE user_id=?
            ''', (self.user_id,)).fetchall()
            conn.close()

            if not courses:
                tk.Label(self.content,
                         text="No courses assigned. Contact admin.",
                         font=("Segoe UI", 12),
                         bg=BG_DARK, fg=TEXT_MUTED).pack(pady=40)
                return

            select_frame = tk.Frame(self.content, bg=BG_DARK,
                                    padx=30, pady=20)
            select_frame.pack(fill="x")
            tk.Label(select_frame, text="Select Course:",
                     font=("Segoe UI", 11, "bold"),
                     bg=BG_DARK, fg=TEXT_PRIMARY).pack(side="left")

            self.course_var = tk.StringVar()
            course_options  = [f"{c[1]} — {c[2]}" for c in courses]
            self.course_ids = [c[0] for c in courses]
            self.course_var.set(course_options[0])

            self.course_combo = ttk.Combobox(
                select_frame,
                textvariable=self.course_var,
                values=course_options,
                state="readonly",
                font=("Segoe UI", 11),
                width=35)
            self.course_combo.pack(side="left", padx=10)

        center = tk.Frame(self.content, bg=BG_DARK)
        center.pack(expand=True)
        tk.Label(center, text="📷",
                 font=("Segoe UI", 64),
                 bg=BG_DARK).pack(pady=10)
        tk.Label(center,
                 text="Click Start Scanner to open camera",
                 font=("Segoe UI", 13),
                 bg=BG_DARK, fg=TEXT_MUTED).pack()

        self.scanner_status = tk.Label(
            center, text="",
            font=("Segoe UI", 12),
            bg=BG_DARK, fg=SUCCESS)
        self.scanner_status.pack(pady=10)

        tk.Button(center, text="  ▶  Start Scanner  ",
                  font=("Segoe UI", 13, "bold"),
                  bg=ACCENT, fg=WHITE,
                  activebackground=ACCENT_HOVER,
                  relief="flat", pady=12, padx=20,
                  cursor="hand2",
                  command=self.launch_scanner).pack(pady=10)

        tk.Label(center,
                 text="Press Q in the camera window to stop.",
                 font=("Segoe UI", 10),
                 bg=BG_DARK, fg=TEXT_MUTED).pack()

    def scan_for_course(self, course_id):
        self.show_scanner()
        if self.role == "lecturer" and hasattr(self, "course_ids"):
            if course_id in self.course_ids:
                idx = self.course_ids.index(course_id)
                self.course_combo.current(idx)

    def launch_scanner(self):
        course_id = None
        if self.role == "lecturer" and hasattr(self, "course_var"):
            try:
                selected = self.course_var.get()
                code = selected.split(" — ")[0]
                conn = create_connection()
                row  = conn.execute(
                    "SELECT id FROM courses WHERE course_code=?",
                    (code,)).fetchone()
                conn.close()
                if row:
                    course_id = row[0]
            except Exception:
                pass

        self.scanner_status.config(
            text="📷 Scanner running... Press Q to stop",
            fg=WARNING)
        self.root.update()

        def run():
            start_scanner(
                status_callback=self.update_scanner_status,
                course_id=course_id)

        threading.Thread(target=run, daemon=True).start()

    def update_scanner_status(self, message):
        try:
            self.scanner_status.config(text=message)
        except Exception:
            pass

    # ── ATTENDANCE ────────────────────────────────────────────────
    def show_attendance(self):
        self.clear_content()
        self.page_header("Attendance Records",
                         "View and filter attendance")

        filter_frame = tk.Frame(self.content, bg=BG_DARK,
                                padx=30, pady=15)
        filter_frame.pack(fill="x")

        tk.Label(filter_frame, text="Date (YYYY-MM-DD):",
                 font=("Segoe UI", 10),
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(side="left")

        self.date_entry = tk.Entry(
            filter_frame, font=("Segoe UI", 11),
            bg=BG_CARD, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat", bd=8, width=15)
        self.date_entry.insert(
            0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(side="left", padx=10)

        tk.Button(filter_frame, text="Filter",
                  font=("Segoe UI", 10),
                  bg=ACCENT, fg=WHITE, relief="flat",
                  padx=15, pady=5, cursor="hand2",
                  command=self.filter_attendance).pack(
                      side="left", padx=5)
        tk.Button(filter_frame, text="Show All",
                  font=("Segoe UI", 10),
                  bg=BG_CARD, fg=TEXT_PRIMARY,
                  relief="flat", padx=15, pady=5,
                  cursor="hand2",
                  command=self.show_all_attendance).pack(
                      side="left", padx=5)

        self.att_table_frame = tk.Frame(
            self.content, bg=BG_DARK, padx=30)
        self.att_table_frame.pack(
            fill="both", expand=True, pady=10)

        if self.role == "lecturer":
            conn = create_connection()
            courses = conn.execute(
                "SELECT id FROM courses WHERE user_id=?",
                (self.user_id,)).fetchall()
            conn.close()
            records = []
            for c in courses:
                records += get_attendance_by_course(
                    c[0],
                    datetime.now().strftime("%Y-%m-%d"))
        else:
            records = get_attendance_by_date()

        self.build_table(
            self.att_table_frame,
            ["Student ID", "Name", "Department",
             "Level", "Date", "Time", "Status"],
            records)

    def filter_attendance(self):
        date = self.date_entry.get().strip()
        if self.role == "lecturer":
            conn = create_connection()
            courses = conn.execute(
                "SELECT id FROM courses WHERE user_id=?",
                (self.user_id,)).fetchall()
            conn.close()
            records = []
            for c in courses:
                records += get_attendance_by_course(c[0], date)
        else:
            records = get_attendance_by_date(date)
        for w in self.att_table_frame.winfo_children():
            w.destroy()
        self.build_table(
            self.att_table_frame,
            ["Student ID", "Name", "Department",
             "Level", "Date", "Time", "Status"],
            records)

    def show_all_attendance(self):
        if self.role == "lecturer":
            conn = create_connection()
            courses = conn.execute(
                "SELECT id FROM courses WHERE user_id=?",
                (self.user_id,)).fetchall()
            conn.close()
            records = []
            for c in courses:
                records += get_attendance_by_course(c[0])
        else:
            records = get_all_attendance()
        for w in self.att_table_frame.winfo_children():
            w.destroy()
        self.build_table(
            self.att_table_frame,
            ["Student ID", "Name", "Department",
             "Level", "Date", "Time", "Status"],
            records)

    # ── REPORTS ───────────────────────────────────────────────────
    def show_reports(self):
        self.clear_content()
        self.page_header("Reports",
                         "Generate and export attendance reports")

        center = tk.Frame(self.content, bg=BG_DARK,
                          padx=30, pady=20)
        center.pack(fill="both", expand=True)

        tk.Label(center, text="Attendance Summary Per Student",
                 font=("Segoe UI", 13, "bold"),
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(
                     anchor="w", pady=(0, 8))

        self.build_table(
            center,
            ["Student ID", "Name", "Department",
             "Level", "Total Present"],
            get_summary_report())

        btn_frame = tk.Frame(center, bg=BG_DARK, pady=15)
        btn_frame.pack(fill="x")

        self.report_status = tk.Label(
            btn_frame, text="",
            font=("Segoe UI", 10),
            bg=BG_DARK, fg=SUCCESS)
        self.report_status.pack(anchor="w", pady=5)

        tk.Button(btn_frame,
                  text="  📥  Export Today to Excel  ",
                  font=("Segoe UI", 11, "bold"),
                  bg="#059669", fg=WHITE,
                  relief="flat", pady=10, padx=10,
                  cursor="hand2",
                  command=self.export_today).pack(
                      side="left", padx=(0, 10))

        tk.Button(btn_frame,
                  text="  📥  Export All Records  ",
                  font=("Segoe UI", 11, "bold"),
                  bg=ACCENT, fg=WHITE,
                  relief="flat", pady=10, padx=10,
                  cursor="hand2",
                  command=self.export_all).pack(side="left")

    def export_today(self):
        date = datetime.now().strftime("%Y-%m-%d")
        success, msg = export_to_excel(date_filter=date)
        self.report_status.config(
            text=msg, fg=SUCCESS if success else ERROR)

    def export_all(self):
        success, msg = export_to_excel()
        self.report_status.config(
            text=msg, fg=SUCCESS if success else ERROR)

    # ── ALL STUDENTS ──────────────────────────────────────────────
    def show_students(self):
        self.clear_content()
        self.page_header("All Students",
                         "View all registered students")

        search_frame = tk.Frame(self.content, bg=BG_DARK,
                                padx=30, pady=15)
        search_frame.pack(fill="x")
        tk.Label(search_frame, text="Search:",
                 font=("Segoe UI", 10),
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(side="left")

        self.search_entry = tk.Entry(
            search_frame, font=("Segoe UI", 11),
            bg=BG_CARD, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat", bd=8, width=25)
        self.search_entry.pack(side="left", padx=10)

        tk.Button(search_frame, text="Search",
                  font=("Segoe UI", 10),
                  bg=ACCENT, fg=WHITE, relief="flat",
                  padx=15, pady=5, cursor="hand2",
                  command=self.do_search).pack(
                      side="left", padx=5)
        tk.Button(search_frame, text="Show All",
                  font=("Segoe UI", 10),
                  bg=BG_CARD, fg=TEXT_PRIMARY,
                  relief="flat", padx=15, pady=5,
                  cursor="hand2",
                  command=self.refresh_students).pack(
                      side="left", padx=5)

        self.students_frame = tk.Frame(
            self.content, bg=BG_DARK, padx=30)
        self.students_frame.pack(
            fill="both", expand=True, pady=10)
        self.refresh_students()

    def do_search(self):
        results = search_student(
            self.search_entry.get().strip())
        for w in self.students_frame.winfo_children():
            w.destroy()
        self.build_table(
            self.students_frame,
            ["Student ID", "Name", "Department",
             "Level", "Email"],
            results)

    def refresh_students(self):
        for w in self.students_frame.winfo_children():
            w.destroy()
        self.build_table(
            self.students_frame,
            ["Student ID", "Name", "Department",
             "Level", "Email"],
            get_all_students())

    # ── REGISTRATION ──────────────────────────────────────────────
    def show_registration(self):
        self.clear_content()
        self.page_header("Register Student",
                         "Add a new student and generate their QR code")

        form_frame = tk.Frame(self.content, bg=BG_CARD,
                              padx=40, pady=30)
        form_frame.pack(padx=30, pady=20, fill="x")

        fields = [
            ("Student ID",  "e.g. STU003"),
            ("Full Name",   "e.g. Jane Smith"),
            ("Department",  "e.g. Computer Science"),
            ("Level",       "e.g. 400"),
            ("Email",       "e.g. jane@uni.com"),
        ]

        self.reg_entries = {}
        for i, (label, ph) in enumerate(fields):
            tk.Label(form_frame, text=label,
                     font=("Segoe UI", 10, "bold"),
                     bg=BG_CARD, fg=TEXT_PRIMARY).grid(
                         row=i, column=0, sticky="w",
                         pady=8, padx=(0, 20))
            entry = tk.Entry(
                form_frame, font=("Segoe UI", 11),
                bg=BG_DARK, fg=TEXT_MUTED,
                insertbackground=TEXT_PRIMARY,
                relief="flat", bd=8, width=35)
            entry.insert(0, ph)
            entry.bind("<FocusIn>",
                       lambda e, en=entry,
                       p=ph: self.clear_ph(en, p))
            entry.bind("<FocusOut>",
                       lambda e, en=entry,
                       p=ph: self.restore_ph(en, p))
            entry.grid(row=i, column=1, sticky="ew", pady=8)
            self.reg_entries[label] = entry

        self.reg_status = tk.Label(
            form_frame, text="",
            font=("Segoe UI", 10),
            bg=BG_CARD, fg=SUCCESS)
        self.reg_status.grid(
            row=len(fields), column=0,
            columnspan=2, pady=10)

        tk.Button(
            form_frame,
            text="  Register Student & Generate QR  ",
            font=("Segoe UI", 12, "bold"),
            bg=ACCENT, fg=WHITE,
            activebackground=ACCENT_HOVER,
            relief="flat", pady=10, cursor="hand2",
            command=self.do_registration).grid(
                row=len(fields)+1, column=0,
                columnspan=2, pady=10)

    def clear_ph(self, entry, ph):
        if entry.get() == ph:
            entry.delete(0, tk.END)
            entry.config(fg=TEXT_PRIMARY)

    def restore_ph(self, entry, ph):
        if entry.get() == "":
            entry.insert(0, ph)
            entry.config(fg=TEXT_MUTED)

    def do_registration(self):
        placeholders = {
            "Student ID": "e.g. STU003",
            "Full Name":  "e.g. Jane Smith",
            "Department": "e.g. Computer Science",
            "Level":      "e.g. 400",
            "Email":      "e.g. jane@uni.com",
        }
        values = {}
        for field, entry in self.reg_entries.items():
            val = entry.get().strip()
            if val == placeholders[field] or not val:
                self.reg_status.config(
                    text=f"❌ Please fill in {field}",
                    fg=ERROR)
                return
            values[field] = val

        success, message = register_student(
            values["Student ID"], values["Full Name"],
            values["Department"], values["Level"],
            values["Email"])
        self.reg_status.config(
            text=message,
            fg=SUCCESS if success else ERROR)
        if success:
            for entry in self.reg_entries.values():
                entry.delete(0, tk.END)

    # ── LECTURERS ─────────────────────────────────────────────────
    def show_lecturers(self):
        self.clear_content()
        self.page_header("Manage Lecturers",
                         "Add and view lecturer accounts")

        form = tk.Frame(self.content, bg=BG_CARD,
                        padx=30, pady=20)
        form.pack(padx=30, pady=15, fill="x")

        tk.Label(form, text="Add New Lecturer",
                 font=("Segoe UI", 12, "bold"),
                 bg=BG_CARD, fg=TEXT_PRIMARY).grid(
                     row=0, column=0, columnspan=8,
                     sticky="w", pady=(0, 10))

        lect_fields = [
            ("Full Name", "e.g. Dr. John",  ""),
            ("Username",  "e.g. john_doe",  ""),
            ("Email",     "e.g. john@uni",  ""),
            ("Password",  "e.g. pass1234",  "•"),
        ]
        self.lect_entries = {}
        for i, (label, ph, show) in enumerate(lect_fields):
            tk.Label(form, text=label,
                     font=("Segoe UI", 10, "bold"),
                     bg=BG_CARD, fg=TEXT_PRIMARY).grid(
                         row=1, column=i*2,
                         sticky="w", padx=(0, 5))
            entry = tk.Entry(
                form, font=("Segoe UI", 10),
                bg=BG_DARK, fg=TEXT_MUTED,
                insertbackground=TEXT_PRIMARY,
                relief="flat", bd=6, width=18,
                show=show)
            entry.insert(0, ph)
            entry.bind("<FocusIn>",
                       lambda e, en=entry,
                       p=ph: self.clear_ph(en, p))
            entry.bind("<FocusOut>",
                       lambda e, en=entry,
                       p=ph: self.restore_ph(en, p))
            entry.grid(row=2, column=i*2,
                       sticky="ew", padx=(0, 15), pady=5)
            self.lect_entries[label] = entry

        self.lect_status = tk.Label(
            form, text="",
            font=("Segoe UI", 10),
            bg=BG_CARD, fg=SUCCESS)
        self.lect_status.grid(
            row=3, column=0, columnspan=8, pady=5)

        tk.Button(form, text="  ➕  Add Lecturer  ",
                  font=("Segoe UI", 11, "bold"),
                  bg=ACCENT, fg=WHITE, relief="flat",
                  pady=8, cursor="hand2",
                  command=self.do_add_lecturer).grid(
                      row=4, column=0,
                      columnspan=8, sticky="w", pady=5)

        self.lect_table_frame = tk.Frame(
            self.content, bg=BG_DARK, padx=30)
        self.lect_table_frame.pack(
            fill="both", expand=True, pady=10)
        self.refresh_lecturers()

    def do_add_lecturer(self):
        placeholders = {
            "Full Name": "e.g. Dr. John",
            "Username":  "e.g. john_doe",
            "Email":     "e.g. john@uni",
            "Password":  "e.g. pass1234",
        }
        values = {}
        for field, entry in self.lect_entries.items():
            val = entry.get().strip()
            if val == placeholders[field] or not val:
                self.lect_status.config(
                    text=f"❌ Please fill in {field}",
                    fg=ERROR)
                return
            values[field] = val

        conn = create_connection()
        try:
            conn.execute('''
                INSERT INTO users
                (username, password, full_name, email, role)
                VALUES (?, ?, ?, ?, 'lecturer')
            ''', (values["Username"],
                  generate_password_hash(values["Password"]),
                  values["Full Name"],
                  values["Email"]))
            conn.commit()
            self.lect_status.config(
                text=f"✅ Lecturer '{values['Full Name']}' added!",
                fg=SUCCESS)
            self.refresh_lecturers()
        except Exception as e:
            self.lect_status.config(
                text=f"❌ {str(e)}", fg=ERROR)
        finally:
            conn.close()

    def refresh_lecturers(self):
        for w in self.lect_table_frame.winfo_children():
            w.destroy()
        conn = create_connection()
        lecturers = conn.execute(
            "SELECT id, username, full_name, email "
            "FROM users WHERE role='lecturer'"
        ).fetchall()
        conn.close()
        self.build_table(
            self.lect_table_frame,
            ["ID", "Username", "Full Name", "Email"],
            lecturers)

    # ── COURSES ───────────────────────────────────────────────────
    def show_courses(self):
        self.clear_content()
        self.page_header("Manage Courses",
                         "Create and assign courses to lecturers")

        form = tk.Frame(self.content, bg=BG_CARD,
                        padx=30, pady=20)
        form.pack(padx=30, pady=15, fill="x")

        tk.Label(form, text="Add New Course",
                 font=("Segoe UI", 12, "bold"),
                 bg=BG_CARD, fg=TEXT_PRIMARY).grid(
                     row=0, column=0, columnspan=6,
                     sticky="w", pady=(0, 10))

        tk.Label(form, text="Course Code",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_CARD, fg=TEXT_PRIMARY).grid(
                     row=1, column=0, sticky="w", padx=(0, 5))
        self.ccode_entry = tk.Entry(
            form, font=("Segoe UI", 10),
            bg=BG_DARK, fg=TEXT_MUTED,
            insertbackground=TEXT_PRIMARY,
            relief="flat", bd=6, width=14)
        self.ccode_entry.insert(0, "e.g. CSC401")
        self.ccode_entry.bind(
            "<FocusIn>",
            lambda e: self.clear_ph(
                self.ccode_entry, "e.g. CSC401"))
        self.ccode_entry.bind(
            "<FocusOut>",
            lambda e: self.restore_ph(
                self.ccode_entry, "e.g. CSC401"))
        self.ccode_entry.grid(
            row=2, column=0, sticky="ew",
            padx=(0, 15), pady=5)

        tk.Label(form, text="Course Name",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_CARD, fg=TEXT_PRIMARY).grid(
                     row=1, column=1, sticky="w", padx=(0, 5))
        self.cname_entry = tk.Entry(
            form, font=("Segoe UI", 10),
            bg=BG_DARK, fg=TEXT_MUTED,
            insertbackground=TEXT_PRIMARY,
            relief="flat", bd=6, width=25)
        self.cname_entry.insert(0, "e.g. Database Systems")
        self.cname_entry.bind(
            "<FocusIn>",
            lambda e: self.clear_ph(
                self.cname_entry, "e.g. Database Systems"))
        self.cname_entry.bind(
            "<FocusOut>",
            lambda e: self.restore_ph(
                self.cname_entry, "e.g. Database Systems"))
        self.cname_entry.grid(
            row=2, column=1, sticky="ew",
            padx=(0, 15), pady=5)

        tk.Label(form, text="Assign Lecturer",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_CARD, fg=TEXT_PRIMARY).grid(
                     row=1, column=2, sticky="w")

        conn = create_connection()
        lecturers = conn.execute(
            "SELECT id, full_name FROM users "
            "WHERE role='lecturer'"
        ).fetchall()
        conn.close()

        self.lect_var = tk.StringVar()
        lect_names   = [l[1] for l in lecturers]
        self.lect_map = {l[1]: l[0] for l in lecturers}
        if lect_names:
            self.lect_var.set(lect_names[0])

        ttk.Combobox(
            form, textvariable=self.lect_var,
            values=lect_names, state="readonly",
            font=("Segoe UI", 10), width=20).grid(
                row=2, column=2, sticky="ew",
                padx=(0, 15), pady=5)

        self.course_status = tk.Label(
            form, text="",
            font=("Segoe UI", 10),
            bg=BG_CARD, fg=SUCCESS)
        self.course_status.grid(
            row=3, column=0, columnspan=3, pady=5)

        tk.Button(form, text="  ➕  Add Course  ",
                  font=("Segoe UI", 11, "bold"),
                  bg=ACCENT, fg=WHITE, relief="flat",
                  pady=8, cursor="hand2",
                  command=self.do_add_course).grid(
                      row=4, column=0, sticky="w", pady=5)

        self.courses_table_frame = tk.Frame(
            self.content, bg=BG_DARK, padx=30)
        self.courses_table_frame.pack(
            fill="both", expand=True, pady=10)
        self.refresh_courses()

    def do_add_course(self):
        code = self.ccode_entry.get().strip()
        name = self.cname_entry.get().strip()
        lect = self.lect_var.get().strip()

        if not code or code == "e.g. CSC401":
            self.course_status.config(
                text="❌ Enter course code", fg=ERROR)
            return
        if not name or name == "e.g. Database Systems":
            self.course_status.config(
                text="❌ Enter course name", fg=ERROR)
            return
        if not lect or lect not in self.lect_map:
            self.course_status.config(
                text="❌ Select a lecturer", fg=ERROR)
            return

        conn = create_connection()
        try:
            conn.execute('''
                INSERT INTO courses
                (course_code, course_name, user_id)
                VALUES (?, ?, ?)
            ''', (code.upper(), name, self.lect_map[lect]))
            conn.commit()
            self.course_status.config(
                text=f"✅ Course '{code.upper()}' created!",
                fg=SUCCESS)
            self.refresh_courses()
        except Exception as e:
            self.course_status.config(
                text=f"❌ {str(e)}", fg=ERROR)
        finally:
            conn.close()

    def refresh_courses(self):
        for w in self.courses_table_frame.winfo_children():
            w.destroy()
        conn = create_connection()
        courses = conn.execute('''
            SELECT c.course_code, c.course_name, u.full_name
            FROM courses c
            LEFT JOIN users u ON c.user_id = u.id
        ''').fetchall()
        conn.close()
        self.build_table(
            self.courses_table_frame,
            ["Course Code", "Course Name", "Lecturer"],
            courses)

    # ── ENROLLMENTS ───────────────────────────────────────────────
    def show_enrollments(self):
        self.clear_content()
        self.page_header("Enroll Students",
                         "Assign students to courses")

        form = tk.Frame(self.content, bg=BG_CARD,
                        padx=30, pady=20)
        form.pack(padx=30, pady=15, fill="x")

        conn = create_connection()
        students = conn.execute(
            "SELECT student_id, name FROM students"
        ).fetchall()
        courses = conn.execute(
            "SELECT id, course_code, course_name FROM courses"
        ).fetchall()
        conn.close()

        tk.Label(form, text="Select Student",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_CARD, fg=TEXT_PRIMARY).grid(
                     row=0, column=0, sticky="w", padx=(0, 10))

        self.enroll_student_var = tk.StringVar()
        student_options  = [f"{s[0]} — {s[1]}" for s in students]
        self.student_id_map = {
            f"{s[0]} — {s[1]}": s[0] for s in students}
        if student_options:
            self.enroll_student_var.set(student_options[0])

        ttk.Combobox(
            form, textvariable=self.enroll_student_var,
            values=student_options, state="readonly",
            font=("Segoe UI", 10), width=30).grid(
                row=1, column=0, sticky="ew",
                padx=(0, 20), pady=5)

        tk.Label(form, text="Select Course",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_CARD, fg=TEXT_PRIMARY).grid(
                     row=0, column=1, sticky="w")

        self.enroll_course_var = tk.StringVar()
        course_options  = [f"{c[1]} — {c[2]}" for c in courses]
        self.course_id_map = {
            f"{c[1]} — {c[2]}": c[0] for c in courses}
        if course_options:
            self.enroll_course_var.set(course_options[0])

        ttk.Combobox(
            form, textvariable=self.enroll_course_var,
            values=course_options, state="readonly",
            font=("Segoe UI", 10), width=30).grid(
                row=1, column=1, sticky="ew",
                padx=(0, 20), pady=5)

        self.enroll_status = tk.Label(
            form, text="",
            font=("Segoe UI", 10),
            bg=BG_CARD, fg=SUCCESS)
        self.enroll_status.grid(
            row=2, column=0, columnspan=2, pady=5)

        tk.Button(form, text="  🔗  Enroll Student  ",
                  font=("Segoe UI", 11, "bold"),
                  bg=ACCENT, fg=WHITE, relief="flat",
                  pady=8, cursor="hand2",
                  command=self.do_enroll).grid(
                      row=3, column=0, sticky="w", pady=5)

        self.enroll_table_frame = tk.Frame(
            self.content, bg=BG_DARK, padx=30)
        self.enroll_table_frame.pack(
            fill="both", expand=True, pady=10)
        self.refresh_enrollments()

    def do_enroll(self):
        student_sel = self.enroll_student_var.get()
        course_sel  = self.enroll_course_var.get()

        if not student_sel or not course_sel:
            self.enroll_status.config(
                text="❌ Select both student and course",
                fg=ERROR)
            return

        student_id = self.student_id_map.get(student_sel)
        course_id  = self.course_id_map.get(course_sel)

        conn = create_connection()
        try:
            conn.execute('''
                INSERT OR IGNORE INTO enrollments
                (student_id, course_id) VALUES (?, ?)
            ''', (student_id, course_id))
            conn.commit()
            self.enroll_status.config(
                text="✅ Student enrolled successfully!",
                fg=SUCCESS)
            self.refresh_enrollments()
        except Exception as e:
            self.enroll_status.config(
                text=f"❌ {str(e)}", fg=ERROR)
        finally:
            conn.close()

    def refresh_enrollments(self):
        for w in self.enroll_table_frame.winfo_children():
            w.destroy()
        conn = create_connection()
        records = conn.execute('''
            SELECT s.student_id, s.name,
                   c.course_code, c.course_name
            FROM enrollments e
            JOIN students s ON e.student_id = s.student_id
            JOIN courses  c ON e.course_id  = c.id
            ORDER BY c.course_code, s.name
        ''').fetchall()
        conn.close()
        self.build_table(
            self.enroll_table_frame,
            ["Student ID", "Name",
             "Course Code", "Course Name"],
            records)

    # ── REUSABLE TABLE ────────────────────────────────────────────
    def build_table(self, parent, columns, rows):
        frame = tk.Frame(parent, bg=BG_DARK)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame, columns=columns,
                            show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center",
                        width=max(100, len(col) * 12))

        for i, row in enumerate(rows):
            tag = "even" if i % 2 == 0 else "odd"
            tree.insert("", "end", values=row, tags=(tag,))

        tree.tag_configure("even", background=BG_CARD)
        tree.tag_configure("odd",  background=BG_DARK)

        sb = ttk.Scrollbar(frame, orient="vertical",
                           command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")


# ── ENTRY POINT ───────────────────────────────────────────────────
if __name__ == "__main__":
    setup_database()
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()