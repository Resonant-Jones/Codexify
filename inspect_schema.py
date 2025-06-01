import sqlite3

conn = sqlite3.connect("guardian.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(memory);")
columns = cursor.fetchall()

print("📋 Memory Table Schema:")
for col in columns:
    cid, name, dtype, notnull, dflt_value, pk = col
    print(f"• {name} ({dtype})")

conn.close()
