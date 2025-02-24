import os
import sys
import psycopg
import time
from datetime import datetime
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
        self.is_currently_rewriting_table = False

    def update_inconveniences_for_everyone(self, request_uuid=None) -> None:
        if request_uuid:
            self.put_request(request_uuid)

        inconveniences = get_IfE(InconvenienceFinder())
        if request_uuid != 'LAUNCH': self._save_inconvenience_changes(inconveniences)
        self.is_currently_rewriting_table = True

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
        self.is_currently_rewriting_table = False
        self._set_all_requests_done()

    def get_inconveniences_for_everyone(self) -> dict[str, dict[str, list[str]]]:
        with psycopg.connect(self.connection_string, autocommit=True) as conn:
            while self.is_currently_rewriting_table:  # if I fetch the data while the table is being rewritten, that data will be incomplete
                time.sleep(1)

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
            while self.is_currently_rewriting_table:  # if I fetch the data while the table is being rewritten, that data will be incomplete
                time.sleep(1)

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

    def get_inconvenience_changes(self) -> list[dict[str]]:
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT dt_noticed, change_type, entity_name, inconvenience_date, message
                FROM inconvenience_changes
                ORDER BY dt_noticed DESC
                ''')
                change_tuples = cursor.fetchall()
        changes = []
        for dt_noticed, change_type, entity_name, inconvenience_date, message in change_tuples:
            changes.append({'dt_noticed': str(dt_noticed),
                            'change_type': change_type,
                            'entity_name': entity_name,
                            'inconvenience_date': inconvenience_date,
                            'message': message})
        return changes

    def put_request(self, request_uuid: str) -> None:
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor() as cursor:
                curr_dt = datetime.now()
                values = (request_uuid, curr_dt, 'Обработка в процессе...')

                cursor.execute('''
                INSERT INTO app_requests
                (request_uuid, dt_submitted, status)
                VALUES (%s, %s, %s)
                ''', values)

    def check_request_status(self, request_uuid: str) -> str:
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT status
                FROM app_requests
                WHERE request_uuid=%s
                ''', (request_uuid,))
                status = cursor.fetchone()
        return status[0] if status else 'Запрос не найден'

    def is_currently_refreshing_data(self) -> bool:
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT * 
                FROM app_requests 
                WHERE status=%s
                ''', ('Обработка в процессе...',))
                response = cursor.fetchall()
        return len(response) > 0

    def _save_inconvenience_changes(self, new_inconveniences: dict[str, dict[str, list[str]]]) -> None:
        old_inconveniences = self.get_inconveniences_for_everyone()
        with (psycopg.connect(self.connection_string) as conn):
            with conn.cursor() as cursor:
                for date in old_inconveniences.keys():
                    for name in old_inconveniences[date].keys():
                        for old_msg in old_inconveniences[date][name]:
                            if (not new_inconveniences.get(date) or
                                    not new_inconveniences[date].get(name) or
                                    old_msg not in new_inconveniences[date][name]):
                                dt_noticed = datetime.now()
                                self._save_change(cursor, dt_noticed, 'Пропало', name, date, old_msg)

                for date in new_inconveniences.keys():
                    for name in new_inconveniences[date].keys():
                        for new_msg in new_inconveniences[date][name]:
                            if (not old_inconveniences.get(date) or
                                    not old_inconveniences[date].get(name) or
                                    new_msg not in old_inconveniences[date][name]):
                                dt_noticed = datetime.now()
                                self._save_change(cursor, dt_noticed, 'Появилось', name, date, new_msg)

    @staticmethod
    def _save_change(cursor, dt_noticed, change_type, name, inconvenience_date, message):
        cursor.execute('''
        INSERT INTO inconvenience_changes
        (dt_noticed, change_type, entity_name, inconvenience_date, message)
        VALUES (%s, %s, %s, %s, %s)
        ''', (dt_noticed, change_type, name, inconvenience_date, message))

    def _set_all_requests_done(self) -> None:
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor() as cursor:
                values = ('Обработка завершена', datetime.now(), 'Обработка в процессе...')
                cursor.execute('''
                UPDATE app_requests 
                SET status = %s, dt_finished = %s
                WHERE status = %s
                ''', values)

    @staticmethod
    def _get_start_dt(start_date: str, inconvenience_msg: str) -> str:
        interval = inconvenience_msg.split()[-1]  # (00:00-12:00)
        start_time = interval.split('-')[0].strip('(')  # 00:00
        return start_date + ' ' + start_time
