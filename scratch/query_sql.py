import sqlite3

for fn in ['customer_data_read_replica_20260921.sql', 'customer_data_failover_replica_20260920.sql', 'customer_data_regional_replicas_20260519.sql']:
    path = f'dataset/evidence/databases/{fn}'
    conn = sqlite3.connect(':memory:')
    with open(path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    for t in tables:
        c.execute(f"SELECT * FROM {t}")
        for row in c.fetchall():
            s = str(row)
            if 'user_50' in s or 'user_48' in s or 'mori.ren' in s or 'akosua.gyasi' in s:
                print(f'{fn} -> {t}: {row}')
