import sqlite3

DB_PATH = "data/hireassist.db"

# Connect to the SQLite database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Show tables
cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name;
""")

tables = cursor.fetchall()

print("Tables:")
for table in tables:
    print(f"  - {table[0]}")

print("\nEnter SQL queries (type 'exit' to quit):")

while True:
    query = input("\nsqlite> ").strip()

    if query.lower() == "exit":
        break

    try:
        cursor.execute(query)

        # SELECT queries
        if query.lower().startswith(("select", "pragma", "with")):
            rows = cursor.fetchall()

            for row in rows:
                print(row)

            print(f"\n{len(rows)} row(s)")

        # INSERT / UPDATE / DELETE etc.
        else:
            conn.commit()
            print(f"{cursor.rowcount} row(s) affected")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

conn.close()