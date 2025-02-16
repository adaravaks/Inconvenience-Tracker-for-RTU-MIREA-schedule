import sys
from type_and_id_parser import TypeAndIdParser
from inconvenience_finder import InconvenienceFinder


def ask_type_and_name() -> tuple:
    s1 = 'Введите 1 для поиска по группам или 2 для поиска по преподавателям: '
    type_ = input(s1)
    s2 = 'Введите название группы строго в формате "АААА-00-00": '
    s3 = 'Введите ФИО преподавателя строго в формате "Фамилия И. О.": '
    if type_ == '1':
        name = input(s2)
    elif type_ == '2':
        name = input(s3)
    else:
        print('Wrong input')
        sys.exit()
    return type_, name.strip()


if __name__ == '__main__':
    id_parser = TypeAndIdParser()
    finder = InconvenienceFinder()

    type_, name = ask_type_and_name()
    try:
        id_ = id_parser.get_id(type_, name)
    except KeyError:
        print('Не найдено такой группы или преподавателя.')
        sys.exit()

    inconveniences = finder.get_all_inconveniences(type_, id_)
    if inconveniences:
        for date in inconveniences.keys():
            print(f'----- {date} -----')
            for inconvenience in inconveniences[date]:
                print(inconvenience)
            print()
    else:
        print('No inconveniences found. Lucky for them!')
