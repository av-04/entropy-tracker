import os
os.environ["DATABASE_URL"] = "postgresql://postgres:entropy@localhost:5433/entropy"
from entropy.storage.db import get_engine
from entropy.storage.models import Base

engine = get_engine()
with engine.connect() as conn:
    print("Dropping tables...")
Base.metadata.drop_all(engine)
print("Tables dropped.")
