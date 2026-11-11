from flask import Flask, render_template, Response, request, redirect, url_for, session, flash, send_file
import cv2
import sqlite3
import csv
import io
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "change-this-demo-secret-key"
DB_NAME = "attendance.db"
CAMERA_INDEX = 1
camera = None

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        department TEXT DEFAULT 'CSD',
        year TEXT DEFAULT 'II',
        status TEXT DEFAULT 'Absent')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL)""")
    if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        sample = [
            ("23CSD001","Arun Kumar","CSD","II","Present"),
            ("23CSD002","Priya S","CSD","II","Present"),
            ("23CSD003","Kavin R","CSD","II","Absent"),
            ("23CSD004","Nila M","CSD","II","Present"),
            ("23CSD005","Hari P","CSD","II","Absent"),
            ("23CSD006","Divya K","CSD","II","Present"),
            ("23CSD007","Santhosh V","CSD","II","Absent"),
            ("23CSD008","Meena R","CSD","II","Present"),
            ("23CSD009","Ajay S","CSD","II","Absent"),
            ("23CSD010","Keerthana P","CSD","II","Present")]
        conn.executemany("INSERT INTO students (student_id,name,department,year,status) VALUES (?,?,?,?,?)", sample)
    conn.commit()
    conn.close()

def log_activity(message):
    conn = get_db()
    conn.execute("INSERT INTO activity (message,created_at) VALUES (?,?)",
                 (message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("home"))
        return func(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username","").strip()
    password = request.form.get("password","")
    if username == "admin" and password == "1234":
        session["logged_in"] = True
        log_activity("Admin logged in")
        return redirect(url_for("dashboard"))
    return render_template("login.html", error="Invalid username or password.")

@app.route("/logout")
def logout():
    if session.get("logged_in"):
        log_activity("Admin logged out")
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    present = conn.execute("SELECT COUNT(*) FROM students WHERE status='Present'").fetchone()[0]
    absent = total - present
    rate = round(present * 100 / total) if total else 0
    recent = conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    return render_template("dashboard.html", total=total, present=present, absent=absent, rate=rate, recent=recent)

@app.route("/students")
@login_required
def students():
    conn = get_db()
    rows = conn.execute("SELECT * FROM students ORDER BY student_id").fetchall()
    conn.close()
    return render_template("students.html", students=rows)

@app.route("/register", methods=["GET","POST"])
@login_required
def register():
    if request.method == "POST":
        student_id = request.form.get("student_id","").strip()
        name = request.form.get("name","").strip()
        department = request.form.get("department","CSD").strip()
        year = request.form.get("year","II").strip()
        if not student_id or not name:
            flash("Student ID and name are required.", "error")
        else:
            conn = get_db()
            try:
                conn.execute("INSERT INTO students (student_id,name,department,year,status) VALUES (?,?,?,?, 'Absent')",
                             (student_id,name,department,year))
                conn.commit()
                conn.close()
                log_activity(f"Registered student {student_id} - {name}")
                flash("Student registered successfully.", "success")
                return redirect(url_for("students"))
            except sqlite3.IntegrityError:
                conn.close()
                flash("That Student ID already exists.", "error")
    return render_template("register.html")

@app.route("/attendance/update/<int:student_pk>", methods=["POST"])
@login_required
def update_attendance(student_pk):
    status = request.form.get("status","Absent")
    if status not in ("Present","Absent"):
        status = "Absent"
    conn = get_db()
    student = conn.execute("SELECT student_id,name FROM students WHERE id=?", (student_pk,)).fetchone()
    if student:
        conn.execute("UPDATE students SET status=? WHERE id=?", (status,student_pk))
        conn.commit()
    conn.close()
    if student:
        log_activity(f"Manual attendance update: {student['student_id']} - {status}")
        flash("Attendance updated. This is a manual demo action, not face-verified.", "success")
    return redirect(url_for("students"))

@app.route("/face-scan")
@login_required
def face_scan():
    return render_template("face_scan.html")

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        try:
            camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
            if not camera.isOpened():
                camera.release()
                camera = cv2.VideoCapture(CAMERA_INDEX)
        except Exception:
            camera = cv2.VideoCapture(CAMERA_INDEX)
    return camera

def generate_frames():
    cam = get_camera()
    while cam is not None and cam.isOpened():
        success, frame = cam.read()
        if not success:
            break
        ok, buffer = cv2.imencode(".jpg", frame)
        if ok:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"

@app.route("/video")
@login_required
def video():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/reports")
@login_required
def reports():
    conn = get_db()
    rows = conn.execute("SELECT student_id,name,department,year,status FROM students ORDER BY student_id").fetchall()
    conn.close()
    return render_template("reports.html", students=rows)

@app.route("/reports/csv")
@login_required
def reports_csv():
    conn = get_db()
    rows = conn.execute("SELECT student_id,name,department,year,status FROM students ORDER BY student_id").fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID","Name","Department","Year","Attendance Status"])
    for row in rows:
        writer.writerow(list(row))
    mem = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="attendance_report.csv")

@app.route("/activity")
@login_required
def activity():
    conn = get_db()
    rows = conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return render_template("activity.html", activities=rows)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, use_reloader=False)
