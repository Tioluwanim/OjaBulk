from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
load_dotenv()
# Use the connection string from your project's .env file
DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL)

with engine.connect() as connection:
    connection.execute(text("DROP SCHEMA public CASCADE;"))
    connection.execute(text("CREATE SCHEMA public;"))
    connection.commit()

print("Database wiped successfully!")