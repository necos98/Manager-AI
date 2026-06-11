import sqlite3
# Check the backend data dir too
conn = sqlite3.connect('backend/data/manager_ai.db')
c = conn.cursor()
try:
    c.execute("SELECT * FROM settings WHERE key LIKE '%queue%' OR key = 'auto_process' OR key = 'work_queue_paused'")
    rows = c.fetchall()
    print('Backend data DB settings:', rows)
except Exception as e:
    print('Backend data DB error:', e)
conn.close()
