import psycopg2
from app.core.config import POSTGRES_PASSWORD

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="scout_db",
        user="postgres",
        password=POSTGRES_PASSWORD
    )
