# 🗄️ Student Attendance & Academic Performance Database System

> A normalised relational database system designed to replace manual attendance tracking — enabling data-driven identification of at-risk students before they fail.

---

## 🔍 Problem Statement

A secondary school was tracking student attendance and academic performance using paper registers and manual spreadsheets. There was no way to quickly identify students with poor attendance, no correlation between attendance and grades, and report preparation took days each term.

The consequence: students who were falling behind were only identified *after* they had already failed — too late for meaningful intervention.

---

## 🎯 Project Objectives

- Design a normalised relational database to store attendance and academic records reliably
- Build SQL queries that surface at-risk students automatically
- Create a reporting layer using Excel and Tableau for staff and management
- Reduce the time spent preparing term reports from days to hours

---

## 🛠️ Tools & Technologies

| Tool | Purpose |
|---|---|
| MySQL / PostgreSQL | Database design and management |
| SQL | Data querying and reporting |
| Python (Pandas) | Data import, cleaning, and analysis |
| Html/CS| Javascript |
| DB Browser / pgAdmin | Database administration |

---

## 🗄️ Database Design

### Entity Relationship Overview

The database is built around five core entities with proper normalisation (3NF):

```
students            classes
├── student_id (PK) ├── class_id (PK)
├── full_name       ├── class_name
├── class_id (FK)   └── form_teacher_id (FK)
├── gender
└── date_of_birth

subjects            teachers
├── subject_id (PK) ├── teacher_id (PK)
├── subject_name    ├── full_name
└── teacher_id (FK) └── subject_id (FK)

attendance
├── attendance_id (PK)
├── student_id (FK → students)
├── date
└── status (Present / Absent / Late)

results
├── result_id (PK)
├── student_id (FK → students)
├── subject_id (FK → subjects)
├── term
├── score
└── grade
```

---

## 🔄 Development Process

### Phase 1 — Requirements Analysis
- Interviewed school management and class teachers
- Mapped existing paper-based workflows to understand data structure needs
- Identified reporting requirements: weekly attendance, term results, at-risk flagging

### Phase 2 — Database Design
- Drew full ER diagram with all entities, attributes, and relationships
- Applied normalisation to 3NF to eliminate redundancy
- Defined primary keys, foreign keys, and constraints

### Phase 3 — Implementation
- Created all tables in MySQL with appropriate data types and constraints
- Imported historical student records from Excel using Python/Pandas
- Cleaned and standardised imported data (name formatting, date formats, class labels)

### Phase 4 — Query Development
- Wrote attendance summary queries by student, class, and date range
- Built at-risk identification queries (attendance below 70% threshold)
- Created term result aggregation queries with automatic grade calculation
- Developed correlation query: attendance rate vs. average score

### Phase 5 — Reporting Layer
- Connected MySQL to Excel for pivot table reporting (used by class teachers)
- Built Tableau dashboard for school management overview
- Documented all queries and provided a user guide for staff

---

## 💻 Key SQL Queries

```sql
-- Identify students with attendance below 70% this term
SELECT
  s.full_name,
  s.class_id,
  COUNT(CASE WHEN a.status = 'Present' THEN 1 END) AS days_present,
  COUNT(a.attendance_id) AS total_days,
  ROUND(COUNT(CASE WHEN a.status = 'Present' THEN 1 END) * 100.0 / COUNT(a.attendance_id), 1) AS attendance_pct
FROM students s
JOIN attendance a ON s.student_id = a.student_id
WHERE a.date BETWEEN '2024-09-01' AND '2024-12-15'
GROUP BY s.student_id, s.full_name, s.class_id
HAVING attendance_pct < 70
ORDER BY attendance_pct ASC;
```

```sql
-- Term result summary with grade per student per subject
SELECT
  s.full_name,
  sub.subject_name,
  r.score,
  CASE
    WHEN r.score >= 70 THEN 'A'
    WHEN r.score >= 60 THEN 'B'
    WHEN r.score >= 50 THEN 'C'
    WHEN r.score >= 40 THEN 'D'
    ELSE 'F'
  END AS grade,
  r.term
FROM results r
JOIN students s ON r.student_id = s.student_id
JOIN subjects sub ON r.subject_id = sub.subject_id
WHERE r.term = 'First Term 2024'
ORDER BY s.full_name, sub.subject_name;
```

```sql
-- Correlation: average attendance rate vs average score per student
SELECT
  s.full_name,
  ROUND(AVG(r.score), 1) AS avg_score,
  ROUND(COUNT(CASE WHEN a.status = 'Present' THEN 1 END) * 100.0 / COUNT(a.attendance_id), 1) AS attendance_pct
FROM students s
JOIN results r ON s.student_id = r.student_id
JOIN attendance a ON s.student_id = a.student_id
GROUP BY s.student_id, s.full_name
ORDER BY attendance_pct DESC;
```

---

## 📈 Results & Impact

| Metric | Outcome |
|---|---|
| Report preparation time | ⬇️ 70% reduction (days → hours) |
| At-risk student identification | Now proactive — flagged mid-term, not after results |
| Data loss incidents | Eliminated (previously common with paper records) |
| Staff adoption | All class teachers using the Excel reporting layer |

---

## 📸 Screenshots

![attendance-system](screenshots/attendance-system.png)

---

## 🚀 How to Set Up

```bash
# Clone the repository
git clone https://github.com/Yahwehboi/attendance-database-system.git

# Import the database schema
mysql -u root -p < schema.sql

# Import sample data
mysql -u root -p school_db < sample_data.sql

# Run the Python data import script (for your own data)
pip install pandas mysql-connector-python
python import_data.py
```

---

## 🔮 Future Improvements

- Build a web interface for teachers to mark attendance digitally
- Add automated email/SMS alerts to parents when attendance drops below threshold
- Integrate with the school website result portal
- Add predictive model to forecast end-of-term performance from mid-term data

---

## 👤 Author

**Agboola Anuoluwapo David**
Data Analyst | Web Developer | CS Graduate

- 🌐 Portfolio: [yahwehboi.github.io](https://yahwehboi.github.io)
- 💼 LinkedIn: [linkedin.com/in/anuoluwapo-agboola-b11000195](https://linkedin.com/in/anuoluwapo-agboola-b11000195)
- 📧 agboolaanouluwapo@gmail.com

---

## 📄 License

MIT License — free to use for educational and portfolio purposes.
