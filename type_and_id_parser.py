import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from os.path import isfile
from threading import Thread
from datetime import datetime


class TypeAndIdParser:
    def __init__(self, update_json_on_init=False):
        self._ids_by_type_and_name = {1: {}, 2: {}}  # 1-groups, 2-professors
        if not isfile('ids_by_type_and_name.json') or update_json_on_init:
            self._parse_all_types_and_ids()
            self._json_dump_all()
        else:
            with open('ids_by_type_and_name.json', 'r', encoding='utf-8') as file:
                self._ids_by_type_and_name = json.loads(file.read())

    def get_id(self, entity_type: int, name: str) -> int:
        return self._ids_by_type_and_name[str(entity_type)][name]

    def _json_dump_all(self) -> None:
        with open('ids_by_type_and_name.json', 'w', encoding='utf-8') as file:
            json.dump(self._ids_by_type_and_name, file, ensure_ascii=False)

    def _parse_all_types_and_ids(self) -> None:
        num_of_threads = 500
        for entity_type in range(1, 3):
            for schedule_id in range(1, 6002, num_of_threads):
                if entity_type != 1 and schedule_id > 3000:  # There are way less professors than there are student groups
                    break
                threads = [Thread(target=self._save_name_by_type_and_id, args=(entity_type, schedule_id + i)) for i in range(num_of_threads)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

    def _save_name_by_type_and_id(self, entity_type: int, schedule_id: int) -> None:
        dt = datetime.now()
        session = requests.Session()
        retry = Retry(connect=10 ** 9,backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        r = session.get(f'https://schedule-of.mirea.ru/_next/data/PuqjJjkncpbeEq4Xieazm/index.json?date={dt.year}-{dt.month}-{dt.day}&s={entity_type}_{schedule_id}',
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0'})
        try:
            name = r.json()['pageProps']['scheduleLoadInfo'][0]['title']
            self._ids_by_type_and_name[entity_type][name] = schedule_id
        except IndexError:  # There are ids that do not correspond to any group or professor
            return
