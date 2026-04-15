import os
import sqlite3
import random
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from db_setup import init_db, create_user, authenticate_user
from datetime import date, timedelta, datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# ------------------------------
# MOTIVATIONAL QUOTES
# ------------------------------
MOTIVATIONAL_QUOTES = [
    {"text": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
    {"text": "It does not matter how slowly you go, as long as you do not stop.", "author": "Confucius"},
    {"text": "Discipline is the bridge between goals and accomplishment.", "author": "Jim Rohn"},
    {"text": "Focus on being productive instead of busy.", "author": "Tim Ferriss"},
    {"text": "Your future is created by what you do today, not tomorrow.", "author": "Robert Kiyosaki"},
    {"text": "Small daily improvements over time lead to stunning results.", "author": "Robin Sharma"},
    {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"text": "Don't watch the clock; do what it does. Keep going.", "author": "Sam Levenson"},
    {"text": "Motivation gets you going, but discipline keeps you growing.", "author": "John C. Maxwell"},
    {"text": "Success is the sum of small efforts repeated day in and day out.", "author": "Robert Collier"},
    {"text": "Push yourself, because no one else is going to do it for you.", "author": "Unknown"},
    {"text": "Great things never come from comfort zones.", "author": "Unknown"},
    {"text": "Dream it. Wish it. Do it.", "author": "Unknown"},
    {"text": "Hard work beats talent when talent doesn't work hard.", "author": "Tim Notke"},
    {"text": "Consistency is what transforms average into excellence.", "author": "Unknown"},
    {"text": "You don't have to be great to start, but you have to start to be great.", "author": "Zig Ziglar"},
    {"text": "The pain you feel today will be the strength you feel tomorrow.", "author": "Unknown"},
    {"text": "Study while others are sleeping; work while others are loafing.", "author": "William A. Ward"},
    {"text": "An investment in knowledge pays the best interest.", "author": "Benjamin Franklin"},
    {"text": "Education is the passport to the future.", "author": "Malcolm X"},
    {"text": "Success is not final; failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill"},
    {"text": "The expert in anything was once a beginner.", "author": "Helen Hayes"},
    {"text": "Don't stop when you're tired. Stop when you're done.", "author": "Unknown"},
    {"text": "The harder you work for something, the greater you'll feel when you achieve it.", "author": "Unknown"},
    {"text": "Stay focused, go after your dreams and keep moving toward your goals.", "author": "LL Cool J"},
]


def get_daily_quote():
    """Returns a deterministic quote for today — same quote all day, changes each day."""
    day_of_year = date.today().timetuple().tm_yday
    index = day_of_year % len(MOTIVATIONAL_QUOTES)
    return MOTIVATIONAL_QUOTES[index]

app = Flask(__name__)
app.secret_key = "focuspulse_super_secret_key"

RAILWAY_DIR = "/app/data"
if os.environ.get("RAILWAY_ENVIRONMENT") or os.path.exists(RAILWAY_DIR):
    DATABASE = "/app/data/focuspulse.db"
else:
    DATABASE = "focuspulse.db"

# Initialize database
init_db()


# ------------------------------
# DATABASE CONNECTION HELPER
# ------------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------
# STREAK TRACKING LOGIC
# ------------------------------
def get_user_streak(user_id):
    conn = get_db_connection()
    try:
        user = conn.execute("SELECT current_streak, best_streak, last_active_date FROM users WHERE id = ?", (user_id,)).fetchone()
        
        if not user:
            conn.close()
            return {"current_streak": 0, "best_streak": 0}

        current_streak = user["current_streak"] or 0
        best_streak = user["best_streak"] or 0
        last_active_str = user["last_active_date"]
        
        today_date = date.today()
        yesterday = today_date - timedelta(days=1)
        
        # If they haven't been active today OR yesterday, their streak is broken.
        if last_active_str:
            try:
                last_active_date = datetime.strptime(last_active_str, "%Y-%m-%d").date()
                if last_active_date < yesterday:
                    current_streak = 0
                    conn.execute("UPDATE users SET current_streak = 0 WHERE id = ?", (user_id,))
                    conn.commit()
            except ValueError:
                pass
                
        conn.close()
        return {"current_streak": current_streak, "best_streak": best_streak}
    except Exception as e:
        conn.close()
        print(f"Error getting user streak: {e}")
        return {"current_streak": 0, "best_streak": 0}


def update_user_streak(user_id):
    conn = get_db_connection()
    try:
        user = conn.execute("SELECT current_streak, best_streak, last_active_date FROM users WHERE id = ?", (user_id,)).fetchone()
        
        if not user:
            conn.close()
            return

        today_str = date.today().isoformat()
        last_active_str = user["last_active_date"]
        
        current_streak = user["current_streak"] or 0
        best_streak = user["best_streak"] or 0
        
        if last_active_str == today_str:
            # Already active today, do nothing
            conn.close()
            return
            
        if last_active_str:
            try:
                last_active_date = datetime.strptime(last_active_str, "%Y-%m-%d").date()
                yesterday = date.today() - timedelta(days=1)
                
                if last_active_date == yesterday:
                    # Maintained streak
                    current_streak += 1
                else:
                    # Missed a day, streak resets to 1 (since they were active today)
                    current_streak = 1
            except ValueError:
                current_streak = 1
        else:
            # First time activity
            current_streak = 1
            
        if current_streak > best_streak:
            best_streak = current_streak
            
        conn.execute(
            "UPDATE users SET current_streak = ?, best_streak = ?, last_active_date = ? WHERE id = ?",
            (current_streak, best_streak, today_str, user_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        conn.close()
        print(f"Error updating user streak: {e}")


# ------------------------------
# LOGIN REQUIRED DECORATOR
# ------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ------------------------------
# HOME ROUTE
# ------------------------------
@app.route("/")
def home():
    current_streak = 0
    daily_quote = get_daily_quote()
    if "user_id" in session:
        streak_info = get_user_streak(session["user_id"])
        current_streak = streak_info["current_streak"]
        
    return render_template("index.html", current_streak=current_streak, daily_quote=daily_quote)


# ------------------------------
# OPTIONAL INFO PAGES
# ------------------------------
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/features")
def features():
    return render_template("features.html")


@app.route("/how-it-works")
def how_it_works():
    return render_template("howitworks.html")


@app.route("/benefits")
def benefits():
    return render_template("benefits.html")


@app.route("/team")
def team():
    return render_template("team.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ------------------------------
# SIGNUP ROUTE
# ------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for("signup"))

        user_id = create_user(username, email, password)
        if user_id:
            session["user_id"] = user_id
            session["user_name"] = username
            flash(f"Signup successful! Welcome, {username}", "success")
            return redirect(url_for("home"))
        else:
            flash("Username or Email already exists", "error")
            return redirect(url_for("signup"))

    return render_template("signup.html")


# ------------------------------
# LOGIN ROUTE
# ------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_or_email = request.form["username"].strip()
        password = request.form["password"]

        user = authenticate_user(username_or_email, password)
        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["username"]
            flash(f"Login successful! Welcome back, {user['username']}", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid username/email or password", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


# ------------------------------
# LOGOUT ROUTE
# ------------------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for("home"))


# ------------------------------
# PLANNER ROUTE
# ------------------------------
@app.route("/planner")
@login_required
def planner():
    return render_template("planner.html")


# ------------------------------
# DELETE TASK ROUTE
# ------------------------------
@app.route("/delete-task/<int:task_id>")
@login_required
def delete_task(task_id):
    user_id = session["user_id"]
    conn = get_db_connection()

    conn.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )
    conn.commit()
    conn.close()

    flash("Task deleted successfully.", "success")
    return redirect(url_for("planner"))


# ------------------------------
# UPDATE STATUS ROUTE
# ------------------------------
@app.route("/update-status/<int:task_id>", methods=["POST"])
@login_required
def update_status(task_id):
    user_id = session["user_id"]
    new_status = request.form["status"]

    conn = get_db_connection()
    conn.execute(
        "UPDATE tasks SET status = ? WHERE id = ? AND user_id = ?",
        (new_status, task_id, user_id)
    )
    conn.commit()
    conn.close()

    if new_status == "Completed":
        update_user_streak(user_id)

    flash("Task status updated successfully.", "success")
    return redirect(url_for("planner"))


# ------------------------------
# DASHBOARD ROUTE
# ------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    conn = get_db_connection()

    total_tasks = 0
    completed_tasks = 0
    pending_tasks = 0
    in_progress_tasks = 0
    recent_tasks = []
    focus_minutes_today = 0
    distractions_today = 0

    try:
        total_tasks = conn.execute(
            "SELECT COUNT(*) AS count FROM tasks WHERE user_id = ?",
            (user_id,)
        ).fetchone()["count"]

        completed_tasks = conn.execute(
            "SELECT COUNT(*) AS count FROM tasks WHERE user_id = ? AND status = 'Completed'",
            (user_id,)
        ).fetchone()["count"]

        pending_tasks = conn.execute(
            "SELECT COUNT(*) AS count FROM tasks WHERE user_id = ? AND status = 'Pending'",
            (user_id,)
        ).fetchone()["count"]

        in_progress_tasks = conn.execute(
            "SELECT COUNT(*) AS count FROM tasks WHERE user_id = ? AND status = 'In Progress'",
            (user_id,)
        ).fetchone()["count"]

        recent_tasks = conn.execute(
            """
            SELECT * FROM tasks
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (user_id,)
        ).fetchall()
    except Exception as e:
        print(f"Error fetching dashboard tasks: {e}")

    # Fetch today's focus session totals for the reminder engine seed
    try:
        today_str = date.today().isoformat()
        today_row = conn.execute(
            """
            SELECT COALESCE(SUM(duration), 0) AS total_min,
                   COALESCE(SUM(distraction_count), 0) AS total_dist
            FROM focus_sessions
            WHERE user_id = ?
              AND DATE(created_at) = ?
            """,
            (user_id, today_str)
        ).fetchone()
        focus_minutes_today = int(today_row["total_min"]) if today_row else 0
        distractions_today  = int(today_row["total_dist"]) if today_row else 0
    except Exception as e:
        print(f"Error fetching today focus data: {e}")

    conn.close()

    streak_info = get_user_streak(user_id)

    productivity_score = 0
    if total_tasks > 0:
        productivity_score = round((completed_tasks / total_tasks) * 100)

    daily_quote = get_daily_quote()
    tasks_remaining = total_tasks - completed_tasks

    return render_template(
        "dashboard.html",
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        in_progress_tasks=in_progress_tasks,
        productivity_score=productivity_score,
        recent_tasks=recent_tasks,
        current_streak=streak_info["current_streak"],
        best_streak=streak_info["best_streak"],
        daily_quote=daily_quote,
        focus_minutes_today=focus_minutes_today,
        distractions_today=distractions_today,
        tasks_remaining=tasks_remaining,
    )


# ------------------------------
# FOCUS MODE ROUTE
# ------------------------------
@app.route("/focus")
@login_required
def focus():
    user_id = session["user_id"]
    conn = get_db_connection()

    tasks = []
    recent_sessions = []
    
    try:
        tasks = conn.execute(
            """
            SELECT task_title FROM tasks
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        ).fetchall()
    except Exception as e:
        print(f"Error fetching focus tasks: {e}")

    try:
        recent_sessions = conn.execute(
            """
            SELECT * FROM focus_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (user_id,)
        ).fetchall()
    except Exception as e:
        print(f"Error fetching recent focus sessions: {e}")

    conn.close()
    return render_template("focus.html", tasks=tasks, recent_sessions=recent_sessions)


# ------------------------------
# SAVE FOCUS SESSION ROUTE
# ------------------------------
@app.route("/save-focus-session", methods=["POST"])
@login_required
def save_focus_session():
    user_id = session["user_id"]
    task_title = request.form.get("task_title", "").strip()
    duration = request.form.get("duration", "0").strip()
    distraction_count = request.form.get("distraction_count", "0").strip()
    focus_score = request.form.get("focus_score", "0").strip()
    notes = request.form.get("notes", "").strip()

    try:
        duration = int(duration)
        distraction_count = int(distraction_count)
        focus_score = int(focus_score)
    except ValueError:
        flash("Invalid focus session data.", "error")
        return redirect(url_for("focus"))

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO focus_sessions (user_id, task_title, duration, distraction_count, focus_score, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, task_title, duration, distraction_count, focus_score, notes)
        )
        conn.commit()
    except Exception as e:
        print(f"Error saving focus session: {e}")
        # flash("Could not save session at this time.", "error")
    finally:
        conn.close()

    update_user_streak(user_id)

    flash("Focus session saved successfully!", "success")
    return redirect(url_for("focus"))


# ------------------------------
# DELETE FOCUS SESSION ROUTE
# ------------------------------
@app.route("/delete-focus-session/<int:session_id>")
@login_required
def delete_focus_session(session_id):
    user_id = session["user_id"]
    conn = get_db_connection()

    conn.execute(
        "DELETE FROM focus_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    )
    conn.commit()
    conn.close()

    flash("Focus session deleted successfully.", "success")
    return redirect(url_for("focus"))

    # ------------------------------
# WELLNESS SETUP ROUTE
# ------------------------------
@app.route("/wellness")
@login_required
def wellness():
    user_id = session["user_id"]
    conn = get_db_connection()

    recent_wellness = []
    try:
        recent_wellness = conn.execute(
            """
            SELECT * FROM wellness_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (user_id,)
        ).fetchall()
    except Exception as e:
        print(f"Error fetching wellness: {e}")

    conn.close()
    return render_template("wellness.html", recent_wellness=recent_wellness)


# ------------------------------
# WELLNESS TIMER PAGE
# ------------------------------
@app.route("/wellness-timer")
@login_required
def wellness_timer():
    return render_template("wellness_timer.html")


# ------------------------------
# SAVE WELLNESS SESSION
# ------------------------------
@app.route("/save-wellness-session", methods=["POST"])
@login_required
def save_wellness_session():
    user_id = session["user_id"]

    active_minutes = request.form.get("active_minutes", "0").strip()
    active_seconds = request.form.get("active_seconds", "30").strip()
    rest_seconds = request.form.get("rest_seconds", "10").strip()
    rounds = request.form.get("rounds", "1").strip()
    completed_rounds = request.form.get("completed_rounds", "0").strip()
    total_active_time = request.form.get("total_active_time", "0").strip()

    try:
        active_minutes = int(active_minutes)
        active_seconds = int(active_seconds)
        rest_seconds = int(rest_seconds)
        rounds = int(rounds)
        completed_rounds = int(completed_rounds)
        total_active_time = int(total_active_time)
    except ValueError:
        flash("Invalid wellness session data.", "error")
        return redirect(url_for("wellness"))

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO wellness_sessions
        (user_id, active_minutes, active_seconds, rest_seconds, rounds, completed_rounds, total_active_time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, active_minutes, active_seconds, rest_seconds, rounds, completed_rounds, total_active_time, "Completed")
    )
    conn.commit()
    conn.close()

    flash("Wellness session saved successfully!", "success")
    return redirect(url_for("wellness"))

# ------------------------------
# CALENDAR API ROUTES
# ------------------------------
@app.route("/api/tasks", methods=["GET"])
@login_required
def get_tasks():
    user_id = session["user_id"]
    conn = get_db_connection()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()

    tasks_list = []
    for t in tasks:
        tasks_list.append({
            "id": t["id"],
            "title": t["task_title"],
            "description": t["description"],
            "date": t["deadline"],
            "start_time": t["start_time"],
            "end_time": t["end_time"],
            "priority": t["priority"],
            "category": t["category"],
            "color": t["color"],
            "status": t["status"],
            "reminder": bool(t["reminder"]),
            "repeat_type": t["repeat_type"]
        })
    return jsonify(tasks_list)

@app.route("/api/tasks", methods=["POST"])
@login_required
def create_task():
    user_id = session["user_id"]
    data = request.json

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tasks 
        (user_id, task_title, description, deadline, start_time, end_time, priority, category, color, status, reminder, repeat_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            data.get("title", "Untitled Task"),
            data.get("description", ""),
            data.get("date", ""),
            data.get("start_time", ""),
            data.get("end_time", ""),
            data.get("priority", "Medium"),
            data.get("category", "Study"),
            data.get("color", "#4F46E5"),
            data.get("status", "Pending"),
            int(data.get("reminder", False)),
            data.get("repeat_type", "none")
        )
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({"success": True, "id": new_id})

@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@login_required
def update_task(task_id):
    user_id = session["user_id"]
    data = request.json

    conn = get_db_connection()
    conn.execute(
        """
        UPDATE tasks SET 
        task_title = ?, description = ?, deadline = ?, start_time = ?, end_time = ?, 
        priority = ?, category = ?, color = ?, status = ?, reminder = ?, repeat_type = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            data.get("title"), data.get("description"), data.get("date"),
            data.get("start_time"), data.get("end_time"), data.get("priority"),
            data.get("category"), data.get("color"), data.get("status"),
            int(data.get("reminder", False)), data.get("repeat_type"),
            task_id, user_id
        )
    )
    conn.commit()
    conn.close()

    if data.get("status") == "Completed":
        update_user_streak(user_id)

    return jsonify({"success": True})

@app.route("/statistics")
@login_required
def statistics():
    user_id = session["user_id"]
    conn = get_db_connection()
    
    completed_tasks = 0
    recent_sessions = []
    
    try:
        completed_tasks = conn.execute(
            "SELECT COUNT(*) AS count FROM tasks WHERE user_id = ? AND status = 'Completed'",
            (user_id,)
        ).fetchone()["count"]
        
        recent_sessions = conn.execute(
            """
            SELECT * FROM focus_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (user_id,)
        ).fetchall()
    except Exception as e:
        print(f"Error fetching statistics: {e}")
    
    streak_info = get_user_streak(user_id)
    conn.close()
    
    return render_template("statistics.html", 
        completed_tasks=completed_tasks, 
        recent_sessions=recent_sessions,
        current_streak=streak_info["current_streak"],
        best_streak=streak_info["best_streak"]
    )



# ------------------------------
# EXPENSE TRACKER ROUTE
# ------------------------------
@app.route("/expenses")
@login_required
def expenses():
    return render_template("expenses.html")


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def delete_api_task(task_id):
    user_id = session["user_id"]
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/api/tasks/<int:task_id>/complete", methods=["PATCH"])
@login_required
def toggle_task(task_id):
    user_id = session["user_id"]
    data = request.json

    conn = get_db_connection()
    conn.execute(
        "UPDATE tasks SET status = ? WHERE id = ? AND user_id = ?",
        (data.get("status", "Completed"), task_id, user_id)
    )
    conn.commit()
    conn.close()

    if data.get("status", "Completed") == "Completed":
        update_user_streak(user_id)

    return jsonify({"success": True})


# ------------------------------
# EMAIL NOTIFICATION SYSTEM
# ------------------------------
def send_reminder_email(recipient_email, username, pending_tasks):
    """
    Sends an email to the user with their pending tasks.
    Uses environment variables for SMTP credentials.
    In MOCK mode (if variables are missing), it logs to the console.
    """
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASSWORD")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port   = int(os.environ.get("SMTP_PORT", 587))

    # Build the task list text
    task_list_str = ""
    if pending_tasks:
        for t in pending_tasks:
            task_list_str += f"- {t['task_title']}\n"
    else:
        task_list_str = "- No tasks remaining! Great job.\n"

    # Build Email Content
    msg = MIMEMultipart()
    msg['From'] = email_user or "noreply@focuspulse.app"
    msg['To'] = recipient_email
    msg['Subject'] = "FocusPulse Reminder"

    body = f"""Hello from FocusPulse,

You still have these tasks remaining today:
{task_list_str}
Start your focus session and stay productive."""

    msg.attach(MIMEText(body, 'plain'))

    # CHECK FOR SMTP CONFIG
    if not email_user or not email_pass:
        print("\n" + "="*50)
        print("MOCK EMAIL SENT (SMTP Credentials Missing)")
        print(f"To: {recipient_email}")
        print(f"Subject: {msg['Subject']}")
        print(f"Body:\n{body}")
        print("="*50 + "\n")
        return {"success": True, "mocked": True}

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.send_message(msg)
        return {"success": True, "mocked": False}
    except Exception as e:
        print(f"Failed to send email: {e}")
        return {"success": False, "error": str(e)}

@app.route("/api/reminder/email", methods=["POST"])
@login_required
def trigger_reminder_email():
    """
    Endpoint triggered by the client-side reminder engine.
    Fetches pending tasks and sends an email to the logged-in user.
    """
    user_id = session["user_id"]
    user_name = session.get("user_name", "Student")
    
    conn = get_db_connection()
    try:
        # Get user email
        user = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        email = user["email"]
        
        # Get pending tasks
        pending_tasks = conn.execute(
            "SELECT task_title, deadline FROM tasks WHERE user_id = ? AND status = 'Pending'",
            (user_id,)
        ).fetchall()
        
        # Send the email
        result = send_reminder_email(email, user_name, pending_tasks)
        
        conn.close()
        return jsonify(result)
    except Exception as e:
        print(f"Error in trigger_reminder_email: {e}")
        if conn: conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)