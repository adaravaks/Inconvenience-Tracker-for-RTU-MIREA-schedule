import os
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

sys.path.append(os.getcwd())  # prevents a nasty ModuleNotFoundError for imports below
from postgres_db.handler import DBhandler
from type_and_id_parser import TypeAndIdParser
from inconvenience_finder import InconvenienceFinder
from execution_helper import determine_type


handler = DBhandler()


@asynccontextmanager
async def lifespan(app: FastAPI):  # before the app starts taking requests, it will load/refresh db data
    TypeAndIdParser(update_json_on_init=True)
    handler.update_inconveniences_for_everyone(request_uuid='LAUNCH')
    yield


app = FastAPI(lifespan=lifespan)
scheduler = BackgroundScheduler(executors={'default': ThreadPoolExecutor(max_workers=1)})  # due to max_workers=1, the app will start auto-updating db data only after finishing auto-updating id data
scheduler.start()


def refresh_db_data() -> None:
    print('INFO: started refreshing database')
    handler.update_inconveniences_for_everyone(request_uuid='SELF-UPDATE')
    print('INFO: database refreshed')


def refresh_id_data() -> None:
    print('INFO: started refreshing id data')
    TypeAndIdParser(update_json_on_init=True)
    print('INFO: id data refreshed')


scheduler.add_job(refresh_id_data, 'interval', hours=4)  # id data will be refreshed on startup and then every 4 hours
scheduler.add_job(refresh_db_data, 'interval', hours=4)  # same as id data


@app.get("/inconveniences")
def get_inconveniences(name: str) -> dict[str, list[str]] | dict[str, str]:
    """Responds with JSON containing inconveniences in schedule of a single entity.
       The name of entity must strictly follow pattern of either "АААА-00-00" for student groups or
       "Фамилия И. О." for professors. Parameter field is case-sensitive and punctuation-sensitive.
       Requesting the list of inconveniences of a single entity generally doesn't take more
       than a couple seconds, so this endpoint will always request and fetch fresh data,
       UNLESS the app is currently processing a lot of requests (e.g. refreshing DB),
       in which case the app will fetch data from DB, since making a request for fresh data
       at that time would severely increase response await time"""
    try:
        if handler.is_currently_refreshing_data() and not handler.is_currently_rewriting_table:
            inconveniences = handler.get_inconveniences(name)
        else:
            finder = InconvenienceFinder()
            id_parser = TypeAndIdParser()
            entity_type = determine_type(name)
            schedule_id = id_parser.get_id(entity_type, name)
            inconveniences = finder.get_all_inconveniences(entity_type, schedule_id)
        return inconveniences
    except KeyError:  # If no schedule data for inputted name is found
        return {'message': 'Сущность не найдена. Убедитесь, что параметр запроса строго соответствует формату «АААА-00-00» или «Фамилия И. О.»'}


@app.get('/inconveniences_for_everyone')
def get_inconveniences_for_everyone() -> dict[str, dict[str, list[str]]]:
    """Same as /inconveniences, but returns inconveniences for every professor and every student group in MIREA.
       Always pulls data from DB, so you might think that this data is likely
       irrelevant and can't be trusted, but that's just not true. While DB data is
       not always fresh, it never gets outdated by more than 4 hours.
       Inconvenience Tracker refreshes all schedule data and rewrites DB based on it
       at least 6 times a day (but in reality even more due to
       how GET /current_inconveniences_for_everyone works)"""
    inconveniences = handler.get_inconveniences_for_everyone()
    return inconveniences


@app.get('/current_inconveniences_for_everyone')
def get_current_inconveniences_for_everyone(request_uuid: str = None):
    """If no parameter is passed, forces the app to start refreshing DB inconveniences data,
       and assigns a specific uuid to the request.
       If that uuid is passed as a parameter, app checks on request's status. If DB has already refreshed,
       app will respond with fresh inconveniences data. If not, however, then user will receive a message
       saying that his request is currently being processed"""
    if request_uuid:
        status = handler.check_request_status(request_uuid)

        if status == 'Обработка завершена':
            inconveniences = handler.get_inconveniences_for_everyone()
            return inconveniences
        else:
            return {'status': status}

    else:  # if no uuid is passed, app creates it and assigns it to the request
        request_uuid = str(uuid.uuid4())
        is_refreshing = handler.is_currently_refreshing_data()
        handler.put_request(request_uuid)
        if not is_refreshing:
            scheduler.add_job(handler.update_inconveniences_for_everyone)
        return {'request_uuid': request_uuid}


@app.get('/inconvenience_changes')
def get_inconvenience_changes() -> list[dict[str, str]]:
    """This one is different from the rest, as the response
       contains not current inconveniences, but rather the changes
       that the app has noticed while updating/refreshing schedule data."""
    changes = handler.get_inconvenience_changes()
    return changes
