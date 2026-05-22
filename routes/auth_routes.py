import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from db_setup import get_db_connection
from services.mail_service import send_reset_password_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        
        conn = get_db_connection()
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        
        if user:
            # Generate a secure token
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            
            # Save token to database
            try:
                conn.execute(
                    "INSERT INTO password_resets (user_id, token, expires_at) VALUES (?, ?, ?)",
                    (user["id"], token, expires_at)
                )
                conn.commit()
                
                # Send email
                if send_reset_password_email(email, token):
                    flash("Password reset link has been sent to your email.", "success")
                else:
                    flash("Error sending email. Please try again later.", "error")
            except Exception as e:
                print(f"Error creating reset token: {e}")
                flash("An error occurred. Please try again.", "error")
        else:
            # For security, we don't want to confirm if the email exists or not
            flash("If an account exists with that email, a password reset link has been sent.", "info")
            
        conn.close()
        return redirect(url_for('auth.forgot_password'))
        
    return render_template("forgot_password.html")

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db_connection()
    
    # Check if token is valid
    reset_request = conn.execute(
        "SELECT * FROM password_resets WHERE token = ? AND used = 0",
        (token,)
    ).fetchone()
    
    if not reset_request:
        conn.close()
        flash("Invalid or used password reset link.", "error")
        return redirect(url_for('login'))
        
    expires_at = datetime.strptime(reset_request["expires_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expires_at:
        conn.close()
        flash("Password reset link has expired. Please request a new one.", "error")
        return redirect(url_for('auth.forgot_password'))

    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            conn.close()
            return redirect(url_for('auth.reset_password', token=token))
            
        # Update password
        password_hash = generate_password_hash(password)
        try:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, reset_request["user_id"])
            )
            
            # Mark token as used
            conn.execute(
                "UPDATE password_resets SET used = 1 WHERE id = ?",
                (reset_request["id"],)
            )
            conn.commit()
            flash("Your password has been reset successfully. You can now log in.", "success")
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error resetting password: {e}")
            flash("An error occurred. Please try again.", "error")
            
    conn.close()
    return render_template("reset_password.html", token=token)
