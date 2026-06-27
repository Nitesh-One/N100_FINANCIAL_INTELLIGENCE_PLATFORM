import sqlite3

def inspect_db(path="db/nifty100.db"):
    con = sqlite3.connect(path)
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print("Tables:")
    for t in tables:
        print(f"- {t}")
        cols = list(cur.execute(f"PRAGMA table_info({t})"))
        for col in cols:
            print(f"    {col}")
    con.close()

if __name__ == '__main__':
    inspect_db()
