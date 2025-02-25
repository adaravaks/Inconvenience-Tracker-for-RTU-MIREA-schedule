import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict
from datetime import timedelta, datetime
from icalendar import Calendar, vDatetime, Event
from icalendar.parser import Contentline


class InconvenienceFinder:
    def get_all_inconveniences(self, entity_type: int, schedule_id: int) -> dict[str, list[str]]:
        """Iterates over all days in someone's schedule, looking for possible
           inconveniences in every single one of them"""
        schedules = self._get_schedules_by_type_and_id(entity_type, schedule_id)
        inconveniences_by_date = {}
        for key in schedules.keys():
            day_schedule = schedules[key]
            if 'неделя' in day_schedule[0].get('SUMMARY'):
                day_schedule = day_schedule[1:]
            daily_inconveniences = self._get_daily_inconveniences(day_schedule)
            if daily_inconveniences:
                inconveniences_by_date[key] = daily_inconveniences

        sorted_dates = sorted(inconveniences_by_date.keys(), key=lambda x: datetime.strptime(x, '%Y-%m-%d'))
        sorted_ibd = {date: inconveniences_by_date[date] for date in sorted_dates}
        return sorted_ibd

    def _get_daily_inconveniences(self, schedule: list[Event]) -> list[str]:
        """For each two adjacent lessons in a daily schedule, performs a series of checks
           to determine whether something between these lessons is inconvenient or not"""
        inconveniences = []
        for i in range(len(schedule) - 1):
            lesson1 = schedule[i]
            lesson2 = schedule[i + 1]

            if self._check_for_window(lesson1, lesson2):
                time1 = str(lesson1.end)[11:16]
                time2 = str(lesson2.start)[11:16]
                inconveniences.append(f'Окно ({time1}-{time2})')

            if self._check_for_long_walk_over_short_break(lesson1, lesson2):
                loc1 = str(lesson1.get('LOCATION'))
                loc2 = str(lesson2.get('LOCATION'))
                time1 = str(lesson1.end)[11:16]
                time2 = str(lesson2.start)[11:16]
                inconveniences.append(f'Нужно дойти от {loc1} до {loc2} за 10 минут ' +
                                      f'({time1}-{time2})')

            if self._check_for_campus_switching(lesson1, lesson2):
                campus1 = str(lesson1.get('LOCATION')).split()[-1].strip('( )')
                campus2 = str(lesson2.get('LOCATION')).split()[-1].strip('( )')
                time1 = str(lesson1.end)[11:16]
                time2 = str(lesson2.start)[11:16]
                inconveniences.append(f'Нужно добраться от корпуса {campus1} до корпуса {campus2} ' +
                                      f'({time1}-{time2})')

        return inconveniences

    def _get_schedules_by_type_and_id(self, entity_type: int, schedule_id: int) -> dict[str, list[Event]]:
        """This one might seem unclear, so here's what it does step by step:
           1. Getting the iCal relevant for specific type and id from other function.
           2. Starting to iterate over the events in that iCal. It's important to note that
           the iCal only describes two-week schedule, the rest is derived by applying specific
           recurrence rules for each event in that two-week schedule.
           2.1. Determining how many times should the event repeat itself. Some events are only formal
           and are not the part of the actual schedule, so they should have no recurrences.
           2.2. iCal describes 2-week worth of schedule, and the semester schedule is spanned across 16 weeks,
           so it is only natural to derive the whole schedule by reiterating over the iCal 8 times. That's
           exactly what it does.
           2.2.1. For each 2-week iteration, event dates are calculated accordingly, and then listed on the
           dict which will later be returned. Also, the "exception dates" of all events are being taken
           into consideration.
           3. The resulting dict with all the daily schedules is returned"""
        cal = self._get_ical_by_type_and_id(entity_type, schedule_id)
        daily_calendars = defaultdict(list)  # yyyy-mm-dd: [schedule]

        for event in cal.events:
            if 'неделя' not in event.get('SUMMARY') and 'занятия в дистанционном формате' not in event.get('SUMMARY'):
                summary = event.get('SUMMARY')
                date = str(event.start)[:10]
                iterations = 8 if 'неделя' not in summary and 'занятия' not in summary else 1

                for fortnight in range(iterations):  # fortnight means two weeks, do not confuse with the game fortnite
                    if event.get('EXDATE') is not None:  # if event has certain exception dates
                        exdates = Contentline(event.get('EXDATE').to_ical()).split(',')  # exdates are dates when events do not follow ->
                        exdates = [datetime.strptime(dt[:8], '%Y%m%d') for dt in exdates]  # -> their regular recurrence rules
                        start_dt = str(vDatetime(event.start).to_ical())[2:-1]  # start_dt is the datetime of the very first occurrence of event
                        recurr_dt = datetime.strptime(start_dt[:8], '%Y%m%d') + timedelta(weeks=2*fortnight)  # recurr_dt is the actual date of event
                        if recurr_dt not in exdates:
                            recurr_date = str(recurr_dt)[:10]
                            daily_calendars[recurr_date].append(event)
                    else:
                        daily_calendars[date].append(event)
        return daily_calendars

    @staticmethod
    def _get_ical_by_type_and_id(entity_type: int, schedule_id: int) -> Calendar:
        """Makes a request for a certain entity's schedule"""
        dt = datetime.now()
        session = requests.Session()
        retry = Retry(connect=10**9, backoff_factor=0.5)  # that's right, there can be a billion reconnect attempts in case of connection failure
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        r = session.get(
            f'https://schedule-of.mirea.ru/_next/data/PuqjJjkncpbeEq4Xieazm/index.json?date={dt.year}-{dt.month}-{dt.day}&s={entity_type}_{schedule_id}',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0'})
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

            if ('Е-' in loc1 or 'Е-' in loc2) and not ('Е-' in loc1 and 'Е-' in loc2):  # If going to/from corpus E is required
                return True

            if ('ФОК' in loc1 or 'ФОК' in loc2) and \
                    ('И-' in loc1 or 'И-' in loc2):  # Do I really need to explain that one?
                return True
        return False

    @staticmethod
    def _check_for_campus_switching(lesson1: Event, lesson2: Event) -> bool:
        if not lesson1.get('LOCATION') or not lesson2.get('LOCATION'):  # Sometimes there's no location set for lesson
            return False

        campus1 = str(lesson1.get('LOCATION')).split()[-1].strip('( )')  # Every location has its campus signature at the end
        campus2 = str(lesson2.get('LOCATION')).split()[-1].strip('( )')

        if campus2 != campus1 and campus1 != 'СДО' and campus2 != 'СДО':  # Online lessons != campus switching
            return True
        return False
