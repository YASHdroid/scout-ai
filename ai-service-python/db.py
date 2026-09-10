import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host="localhost",
    database="scout_db",
    user="postgres",
    password=os.getenv("POSTGRES_PASSWORD")
)

print("Database connected successfully!")