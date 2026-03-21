import os
import logging
# force the correct URL
os.environ["DATABASE_URL"] = "postgresql://postgres:entropy@localhost:5433/entropy"

# setup logging to see the logger info output
logging.basicConfig(level=logging.INFO)

from entropy.storage.db import init_db
from entropy.storage.models import Base
from entropy.storage.db import get_engine

# Drop and init
engine = get_engine()
with engine.connect() as conn:
    print("Dropping tables...")
Base.metadata.drop_all(engine)
print("Initializing database...")
init_db()
print("Done.")
