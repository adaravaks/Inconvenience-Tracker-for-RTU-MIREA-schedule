import os
import sys
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

sys.path.append(os.getcwd())  # prevents a nasty ModuleNotFoundError for imports below
from postgres_db.handler import DBhandler
from type_and_id_parser import TypeAndIdParser


handler = DBhandler()


@asynccontextmanager
async def lifespan(app: FastAPI):  # before the app starts taking requests, it will load/refresh db data
    handler.update_inconveniences_for_everyone()
    yield


app = FastAPI(lifespan=lifespan)
scheduler = BackgroundScheduler()
scheduler.start()


def refresh_db_data() -> None:
    print('INFO: started refreshing database')
    handler.update_inconveniences_for_everyone()
    print('INFO: database refreshed')


def refresh_id_data() -> None:
    print('INFO: started refreshing id data')
    TypeAndIdParser(update_json_on_init=True)
    print('INFO: id data refreshed')


scheduler.add_job(refresh_db_data, 'interval', hours=4)  # db data will be refreshed on startup and then every 4 hours
scheduler.add_job(refresh_id_data, 'interval', hours=4)  # same as db data but doesn't refresh on startup


@app.get('/inconveniences_for_everyone')
def get_inconveniences_for_everyone() -> dict[str, dict[str, list[str]]]:
    inconveniences = handler.get_inconveniences_for_everyone()
    return inconveniences


@app.get("/inconveniences")
def get_inconveniences(name: str) -> dict[str, list[str]]:
    inconveniences = handler.get_inconveniences(name)
    return inconveniences
