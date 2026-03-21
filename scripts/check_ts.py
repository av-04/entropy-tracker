import os
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "postgresql://postgres:entropy@localhost:5433/entropy")
engine = create_engine(url)

with engine.connect() as conn:
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
        conn.commit()
        print("Extension created.")
        conn.execute(text("SELECT create_hypertable('module_entropy', 'time', if_not_exists => TRUE, migrate_data => TRUE);"))
        conn.commit()
        print("Hypertable created.")
    except Exception as e:
        print(f"Error: {e}")
