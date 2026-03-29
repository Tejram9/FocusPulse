import traceback
from app import app, get_db_connection

def test_post_focus():
    app.testing = True
    with app.test_client() as client:
        # We need a user to log in
        conn = get_db_connection()
        user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
        conn.close()
        
        if not user:
            print("No user in DB. Skipping login test.")
            return

        with client.session_transaction() as sess:
            sess['user_id'] = user['id']
            sess['user_name'] = "Test User"
            
        print("Testing POST /save-focus-session...")
        try:
            resp = client.post("/save-focus-session", data={
                'task_title': 'Test Task',
                'duration': '25',
                'distraction_count': '0',
                'focus_score': '100',
                'notes': 'test notes'
            })
            print("Status:", resp.status_code)
            if resp.status_code >= 400:
                print(resp.data.decode()[:1000])
        except Exception as e:
            print("Exception during POST /save-focus-session:")
            traceback.print_exc()

if __name__ == "__main__":
    test_post_focus()
