import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
conn_string = (f'host={os.getenv('DB_HOST')} ' +
               f'port={os.getenv('DB_PORT')} ' +
               f'dbname={os.getenv('DB_NAME')} ' +
               f'user={os.getenv('DB_USER')} ' +
               f'password={os.getenv('DB_PASSWORD')}')

default_conn_string = (f'host={os.getenv('DB_HOST')} ' +
                       f'port={os.getenv('DB_PORT')} ' +
                       f'dbname={os.getenv('DB_DEFAULT_NAME')} ' +
                       f'user={os.getenv('DB_USER')} ' +
                       f'password={os.getenv('DB_PASSWORD')}')

try:  # creates the database if it doesn't exist yet
    with psycopg.connect(conn_string) as conn:
        pass
except psycopg.errors.OperationalError:
    with psycopg.connect(default_conn_string, autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE DATABASE inconveniences_in_rtu_mirea_schedule
            """)

with psycopg.connect(conn_string) as conn:
    with conn.cursor() as cur:  # creates the tables if they don't exist yet
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS schedule_ids (
                        id serial PRIMARY KEY,
                        entity_name text,
                        entity_type integer,
                        schedule_id integer)
                    """)

        cur.execute("""
                    CREATE TABLE IF NOT EXISTS inconveniences (
                        id serial PRIMARY KEY,
                        occur_date date,
                        entity_type integer,
                        entity_name text,
                        start_time timestamp,
                        message text)
                    """)
