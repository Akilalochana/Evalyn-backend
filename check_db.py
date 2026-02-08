import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'), cursor_factory=RealDictCursor)
cur = conn.cursor()

print('=== ALL JOBS ===')
cur.execute('SELECT id, title FROM "JobPost" LIMIT 10')
for job in cur.fetchall():
    print(f"  {job['id']}: {job['title']}")

print()
print('=== ALL APPLICATIONS ===')
cur.execute('SELECT column_name FROM information_schema.columns WHERE table_name = %s', ('JobApplication',))
cols = [r['column_name'] for r in cur.fetchall()]
print(f'Columns: {cols}')

cur.execute('SELECT * FROM "JobApplication" LIMIT 5')
for app in cur.fetchall():
    print(f"  {app}")

cur.close()
conn.close()
