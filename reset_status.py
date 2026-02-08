import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute('UPDATE "JobApplication" SET status = %s', ('pending',))
conn.commit()
print('Reset all to pending')
cur.close()
conn.close()
