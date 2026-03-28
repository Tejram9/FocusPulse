import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

RAILWAY_DIR = "/app/data"
if os.environ.get("RAILWAY_ENVIRONMENT") or os.path.exists(RAILWAY_DIR):
    DB_NAME = "/app/data/focuspulse.db"
else:
    DB_NAME = "focuspulse.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON;")

            # ------------------------------
            # USERS TABLE
            # ------------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # ------------------------------
            # TASKS TABLE
            # ------------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_title TEXT NOT NULL,
                subject TEXT,
                deadline TEXT,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

            # ------------------------------
            # FOCUS SESSIONS TABLE
            # ------------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_title TEXT,
                date TEXT DEFAULT (date('now', 'localtime')),
                duration INTEGER NOT NULL,
                distraction_count INTEGER DEFAULT 0,
                focus_score INTEGER DEFAULT 100,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

            # ------------------------------
            # SAFE COLUMN CHECKS FOR WELLNESS SESSIONS
            # ------------------------------
            cursor.execute("PRAGMA table_info(wellness_sessions)")
            wellness_columns = [col["name"] for col in cursor.fetchall()]

            if "created_at" not in wellness_columns:
                cursor.execute("ALTER TABLE wellness_sessions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            # ------------------------------
            # STUDY PLANS TABLE
            # ------------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                planned_time TEXT,
                date TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

# ------------------------------
            # WELLNESS SESSIONS TABLE
            # ------------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS wellness_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                active_minutes INTEGER DEFAULT 0,
                active_seconds INTEGER DEFAULT 30,
                rest_seconds INTEGER DEFAULT 10,
                rounds INTEGER DEFAULT 5,
                completed_rounds INTEGER DEFAULT 0,
                total_active_time INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

            # ------------------------------
            # SAFE COLUMN CHECKS FOR USERS
            # ------------------------------
            cursor.execute("PRAGMA table_info(users)")
            user_columns = [col["name"] for col in cursor.fetchall()]

            if "created_at" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if "current_streak" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN current_streak INTEGER DEFAULT 0")
            if "best_streak" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN best_streak INTEGER DEFAULT 0")
            if "last_active_date" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN last_active_date TEXT")

            # ------------------------------
            # SAFE COLUMN CHECKS FOR TASKS
            # ------------------------------
            cursor.execute("PRAGMA table_info(tasks)")
            task_columns = [col["name"] for col in cursor.fetchall()]

            if "created_at" not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                
            if "description" not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN description TEXT")
            if "start_time" not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN start_time TEXT")
            if "end_time" not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN end_time TEXT")
            if "priority" not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'Medium'")
            if "category" not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT 'Study'")
            if "color" not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN color TEXT DEFAULT '#4F46E5'")
            if "reminder" not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN reminder BOOLEAN DEFAULT 0")
            if "repeat_type" not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN repeat_type TEXT DEFAULT 'none'")

            # ------------------------------
            # SAFE COLUMN CHECKS FOR FOCUS SESSIONS
            # ------------------------------
            cursor.execute("PRAGMA table_info(focus_sessions)")
            focus_columns = [col["name"] for col in cursor.fetchall()]

            if "task_title" not in focus_columns:
                cursor.execute("ALTER TABLE focus_sessions ADD COLUMN task_title TEXT")

            if "distraction_count" not in focus_columns:
                cursor.execute("ALTER TABLE focus_sessions ADD COLUMN distraction_count INTEGER DEFAULT 0")

            if "focus_score" not in focus_columns:
                cursor.execute("ALTER TABLE focus_sessions ADD COLUMN focus_score INTEGER DEFAULT 100")

            if "created_at" not in focus_columns:
                cursor.execute("ALTER TABLE focus_sessions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            conn.commit()
            print("Database schema created successfully.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")


def create_user(username, email, password):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        user_id = None
    finally:
        conn.close()

    return user_id


def authenticate_user(username_or_email, password):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (username_or_email, username_or_email)
    )
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }

    return None


if __name__ == "__main__":
    init_db()