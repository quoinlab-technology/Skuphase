"""Small local database inspection helper; never used by application startup."""

import os

import psycopg2


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("Set DATABASE_URL before running this local inspection helper.")
    conn = psycopg2.connect(database_url.replace("+asyncpg", ""))
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position")
    columns = [row[0] for row in cur.fetchall()]
    print("Current users columns:")
    for column in columns:
        print(" ", column)
    print("token_generation exists:", "token_generation" in columns)
    print("token_valid_after exists:", "token_valid_after" in columns)
    print("last_login exists:", "last_login" in columns)
    cur.execute("SELECT version_num FROM alembic_version")
    row = cur.fetchone()
    print("Alembic version:", row[0] if row else "None")
    conn.close()


if __name__ == "__main__":
    main()
