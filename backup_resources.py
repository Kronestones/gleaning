"""
backup_resources.py — Gleaning Resources Backup
Run anytime to export all resources to CSV on your phone.
python3 backup_resources.py
"""
import os
import csv
from datetime import datetime

os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_JIOfQrgA3Li0@ep-silent-band-amurkch1-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

with engine.connect() as conn:
    rows = conn.execute(text("SELECT * FROM resources ORDER BY category, name")).fetchall()
    keys = rows[0]._mapping.keys() if rows else []

filename = f"resources_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
path = os.path.expanduser(f"~/storage/downloads/{filename}")

with open(path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=keys)
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row._mapping))

print(f"✓ {len(rows)} resources backed up to {path}")
