import psycopg2

conn = psycopg2.connect('postgresql://postgres:evayoung@localhost:5432/skuphase_dev_fresh')
cur = conn.cursor()

cur.execute("""
SELECT column_name FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position
""")
cols = [row[0] for row in cur.fetchall()]
print('Current users columns:')
for c in cols:
    print(' ', c)
print()
print('token_generation exists:', 'token_generation' in cols)
print('token_valid_after exists:', 'token_valid_after' in cols)
print('last_login exists:', 'last_login' in cols)

# Also check the alembic version
cur.execute("SELECT version_num FROM alembic_version")
row = cur.fetchone()
print('Alembic version:', row[0] if row else 'None')
conn.close()
