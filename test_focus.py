import traceback
import sqlite3
from app import app, get_db_connection

def test_focus():
    with app.test_client() as client:
        # We need a user to log in
        conn = get_db_connection()
        user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
        conn.close()
        
        if not user:
            print("No user in DB. Skipping login test, or creating one.")
            return

        with client.session_transaction() as sess:
            sess['user_id'] = user['id']
            sess['user_name'] = "Test User"
            
        print("Testing GET /focus...")
        try:
            resp = client.get("/focus")
            print("Status:", resp.status_code)
            if resp.status_code == 500:
                print(resp.data.decode()[:1000])
        except Exception as e:
            print("Exception during GET /focus:")
            traceback.print_exc()

if __name__ == "__main__":
    app.testing = True
    test_focus()
