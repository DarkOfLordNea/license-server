import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")

def delete_free():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("DELETE FROM licenses WHERE type='FREE'")
    deleted = cur.rowcount

    conn.commit()
    conn.close()

    print("Deleted FREE keys:", deleted)

if __name__ == "__main__":
    delete_free()