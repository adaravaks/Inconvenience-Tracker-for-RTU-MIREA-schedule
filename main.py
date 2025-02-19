import sys
import json
from datetime import datetime
from time import time
from concurrent.futures import ThreadPoolExecutor
from type_and_id_parser import TypeAndIdParser
from inconvenience_finder import InconvenienceFinder


def determine_type(name: str) -> int:
    return 1 if any(char.isdigit() for char in name) else 2


def ask_name() -> str:
    s = 'Введите название группы строго в формате "АААА-00-00" или ФИО преподавателя строго в формате "Фамилия И. О.":'
    name = input(s)
    return name.strip()


def get_inconveniences_for_everyone(finder: InconvenienceFinder) -> dict[str, dict[str, list[str]]]:  # {date: {name: [inconveniences]}}
    with open('ids_by_type_and_name.json', 'r', encoding='utf-8') as f:
        ids_by_type_and_name = json.loads(f.read())
    all_inconveniences_in_mirea = {}

    for type_ in range(2, 0, -1):  # first professors, then students
        with ThreadPoolExecutor(max_workers=800) as executor:
            futures = {}
            for name in ids_by_type_and_name[str(type_)].keys():
                id_ = ids_by_type_and_name[str(type_)][name]
                futures[name] = (executor.submit(finder.get_all_inconveniences, type_, id_))

        for name in futures.keys():
            inconveniences = futures[name].result()
            if inconveniences:
                for date in inconveniences.keys():
                    if not all_inconveniences_in_mirea.get(date): all_inconveniences_in_mirea[date] = {}
                    all_inconveniences_in_mirea[date][name] = inconveniences[date]
    return all_inconveniences_in_mirea


if __name__ == '__main__':
    start = time()
    id_parser = TypeAndIdParser()
    finder = InconvenienceFinder()

    mirea_inconveniences = get_inconveniences_for_everyone(finder)
    dates = sorted(mirea_inconveniences.keys(), key=lambda x: datetime.strptime(x, '%Y-%m-%d'))
    for date in dates:
        print(f'--------------- {date} ---------------')
        for name in mirea_inconveniences[date].keys():
            print(f'    {name}:')
            for inconvenience in mirea_inconveniences[date][name]:
                print(inconvenience)
            print()
    end = time()
    print(end-start)
