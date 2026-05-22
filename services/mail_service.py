from flask_mail import Mail, Message
from flask import render_template, current_app

mail = Mail()

def send_welcome_email(user_email, username):
    """
    Sends a welcome email to the newly registered user.
    """
    try:
        msg = Message(
            subject="Welcome to FocusPulse!",
            recipients=[user_email]
        )
        msg.html = render_template('email/welcome.html', username=username)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending welcome email to {user_email}: {e}")
        return False

def send_reset_password_email(user_email, token):
    """
    Sends a password reset email to the user.
    """
    try:
        msg = Message(
            subject="Reset Your FocusPulse Password",
            recipients=[user_email]
        )
        msg.html = render_template('email/reset_password.html', token=token)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending reset password email to {user_email}: {e}")
        return False

def send_task_reminder_email(user_email, username, pending_tasks):
    """
    Sends a daily task reminder email to the user.
    """
    try:
        msg = Message(
            subject="FocusPulse Daily Reminder",
            recipients=[user_email]
        )
        msg.html = render_template('email/task_reminder.html', username=username, pending_tasks=pending_tasks)
        mail.send(msg)
        return {"success": True, "mocked": False}
    except Exception as e:
        print(f"Error sending task reminder email to {user_email}: {e}")
        return {"success": False, "error": str(e)}
