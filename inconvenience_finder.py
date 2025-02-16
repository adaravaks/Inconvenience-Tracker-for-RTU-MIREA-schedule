from icalendar import Calendar, vDatetime, Event
from icalendar.parser import Contentline
import requests
from collections import defaultdict
from datetime import timedelta, datetime


class InconvenienceFinder:
    def get_all_inconveniences(self, type_: int, id_: int) -> dict[str, list[str]]:
        schedules = self._get_schedules_by_type_and_id(type_, id_)
        inconveniences_by_date = {}
        for key in schedules.keys():
            daily_inconveniences = self._get_daily_inconveniences(schedules[key])
            if daily_inconveniences:
                inconveniences_by_date[key] = daily_inconveniences
        return inconveniences_by_date

    def _get_daily_inconveniences(self, schedule: list[Event]) -> list[str]:
        inconveniences = []
        for i in range(len(schedule) - 1):
            lesson1 = schedule[i]
            lesson2 = schedule[i + 1]

            if self._check_for_window(lesson1, lesson2):
                time1 = str(lesson1.end)[11:16]
                time2 = str(lesson2.end)[11:16]
                inconveniences.append(f'Window from {time1} to {time2}')

            if self._check_for_long_walk_over_short_break(lesson1, lesson2):
                loc1 = str(lesson1.get('LOCATION'))
                loc2 = str(lesson2.get('LOCATION'))
                time1 = str(lesson1.end)[11:16]
                time2 = str(lesson2.start)[11:16]
                inconveniences.append(f'The distance from {loc1} to {loc2} has to be crossed in 10 minutes ' +
                                      f'({time1}-{time2})')

            if self._check_for_campus_switching(lesson1, lesson2):
                campus1 = str(lesson1.get('LOCATION'))[-6:].strip('( )')
                campus2 = str(lesson2.get('LOCATION'))[-6:].strip('( )')
                time1 = str(lesson1.end)[11:16]
                time2 = str(lesson2.start)[11:16]
                inconveniences.append(f'Transfer from {campus1} to {campus2} is required ' +
                                      f'({time1}-{time2})')

        return inconveniences

    def _get_schedules_by_type_and_id(self, type_: int, id_: int) -> dict[str, list[Event]]:
        cal = self._get_ical_by_type_and_id(type_, id_)
        daily_calendars = defaultdict(list)  # yyyy-mm-dd: [schedule]

        for event in cal.events:
            date = str(event.start)[:10]
            if 'неделя' not in event.get('SUMMARY') and 'занятия в дистанционном формате' not in event.get('SUMMARY'):
                if event.get('EXDATE') is not None:  # if event has certain exception dates
                    exdates = Contentline(
                        event.get('EXDATE').to_ical())  # exdates are dates when lessons do not follow ->
                    start_dt = str(vDatetime(event.start).to_ical())[2:-1]  # -> their regular recurrence rules
                    if start_dt not in exdates:
                        daily_calendars[date].append(event)
                else:
                    daily_calendars[date].append(event)
        return daily_calendars

    @staticmethod
    def _get_ical_by_type_and_id(type_: int, id_: int) -> Calendar:
        dt = datetime.now()
        r = requests.get(
            f'https://schedule-of.mirea.ru/_next/data/PuqjJjkncpbeEq4Xieazm/index.json?date={dt.year}-{dt.month}-{dt.day}&s={type_}_{id_}')
        cal_text = r.json()['pageProps']['scheduleLoadInfo'][0]['iCalContent']
        cal = Calendar.from_ical(cal_text)
        return cal

    @staticmethod
    def _check_for_window(lesson1: Event, lesson2: Event) -> bool:
        if lesson2.start - lesson1.end > timedelta(minutes=90):  # If more than 90 minutes passes between lessons
            return True
        return False

    @staticmethod
    def _check_for_long_walk_over_short_break(lesson1: Event, lesson2: Event) -> bool:
        if lesson2.start - lesson1.end == timedelta(minutes=10):  # If it is a short break
            loc1 = str(lesson1.get('LOCATION'))
            loc2 = str(lesson2.get('LOCATION'))

            if 'Е-' in loc1 or 'Е-' in loc2:  # If going to/from corpus E is required
                return True

            if ('ФОК' in loc1 or 'ФОК' in loc2) and \
                    ('И-' in loc1 or 'И-' in loc2):  # Do I really need to explain that one?
                return True
        return False

    @staticmethod
    def _check_for_campus_switching(lesson1: Event, lesson2: Event) -> bool:
        if not lesson1.get('LOCATION') or lesson2.get('LOCATION'):  # Sometimes there's no location set for lesson
            return False

        campus1 = str(lesson1.get('LOCATION'))[-6:].strip('( )')  # Every location has its campus signature at the end
        campus2 = str(lesson2.get('LOCATION'))[-6:].strip('( )')  # 6 last characters are enough to determine the campus

        if campus2 != campus1 and campus1 != 'СДО' and campus2 != 'СДО':  # Online lessons != campus switching
            return True
        return False
