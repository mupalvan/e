import sqlite3

conn = sqlite3.connect("ehsanDBproduct.db")
cursor = conn.cursor()

# Create a table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS feature (
        id INTEGER PRIMARY KEY,
        color TEXT ,
        material TEXT ,
        type TEXT ,
        brand TEXT ,
        guarantee TEXT
    )
""")

# Commit changes
conn.commit()
conn.close()
