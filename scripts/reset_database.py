import os
import sys

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

import psycopg2

from modules.config import DATABASE_URL

tables = ['balance', 'coins', 'headers', 'trades']

conn = psycopg2.connect(DATABASE_URL)

for table in tables:
    cursor = conn.cursor()
    cursor.execute(f"""DROP TABLE IF EXISTS {table} CASCADE""")
    conn.commit()
