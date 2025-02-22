import os
import sys
import psycopg
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.getcwd())  # prevents a nasty ModuleNotFoundError for imports below
from inconvenience_finder import InconvenienceFinder
from main import determine_type, get_inconveniences_for_everyone as get_IfE


class DBhandler:
    def __init__(self):
        self.connection_string = (f'host={os.getenv('DB_HOST')} ' +
                                  f'port={os.getenv('DB_PORT')} ' +
                                  f'dbname={os.getenv('DB_NAME')} ' +
                                  f'user={os.getenv('DB_USER')} ' +
                                  f'password={os.getenv('DB_PASSWORD')}')

    def update_inconveniences_for_everyone(self) -> None:
        inconveniences = get_IfE(InconvenienceFinder())
        with psycopg.connect(self.connection_string, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                TRUNCATE TABLE inconveniences RESTART IDENTITY
                ''')

            for date in inconveniences.keys():
                for name in inconveniences[date].keys():
                    entity_type = determine_type(name)
                    for inconvenience_msg in inconveniences[date][name]:
                        start_dt = self._get_start_dt(date, inconvenience_msg)

                        values = (date, entity_type, name, start_dt, inconvenience_msg)
                        with conn.cursor() as cursor:
                            cursor.execute('''
                            INSERT INTO inconveniences 
                            (occur_date, entity_type, entity_name, start_time, message)
                            VALUES (%s, %s, %s, %s, %s)
                            ''', values)

    def get_inconveniences_for_everyone(self) -> dict[str, dict[str, list[str]]]:
        with psycopg.connect(self.connection_string, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SElECT occur_date, entity_name, message 
                FROM inconveniences  
                ORDER BY occur_date, entity_type DESC, entity_name, start_time 
                ''')
                inconv_tuples = cursor.fetchall()

        inconveniences = defaultdict(lambda: defaultdict(list))
        for date, name, message in inconv_tuples:
            inconveniences[str(date)][name].append(message)

        return inconveniences

    def get_inconveniences(self, name: str) -> dict[str, list[str]]:
        with psycopg.connect(self.connection_string, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SElECT occur_date, message
                FROM inconveniences
                WHERE entity_name=%s
                ORDER BY occur_date, start_time
                ''', (name,))
                inconv_tuples = cursor.fetchall()

        inconveniences = defaultdict(list)
        for date, message in inconv_tuples:
            inconveniences[str(date)].append(message)
        return inconveniences

    @staticmethod
    def _get_start_dt(start_date: str, inconvenience_msg: str) -> str:
        interval = inconvenience_msg.split()[-1]  # (00:00-12:00)
        start_time = interval.split('-')[0].strip('(')  # 00:00
        return start_date + ' ' + start_time
