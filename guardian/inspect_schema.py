import logging
import sqlite3

logger = logging.getLogger(__name__)

conn = sqlite3.connect("guardian.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(memory);")
columns = cursor.fetchall()

logger.info("Memory Table Schema:")
for col in columns:
    cid, name, dtype, notnull, dflt_value, pk = col
    logger.info(f"  {name} ({dtype})")

conn.close()
