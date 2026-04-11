import psycopg2
import os

try:
    # Test connection to Supabase via Pooler (Port 6543) which usually supports IPv4
    conn = psycopg2.connect(
        "postgresql://postgres:Bezeguinho*1974@db.zzzkeivrpuzdsqivqzjm.supabase.co:6543/postgres",
        connect_timeout=10
    )
    print("Connection successful on port 6543!")
    conn.close()
except Exception as e:
    print(f"Connection failed on port 6543: {e}")
