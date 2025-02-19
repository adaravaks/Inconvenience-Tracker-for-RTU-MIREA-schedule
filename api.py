from fastapi import FastAPI
from .inconvenience_finder import InconvenienceFinder
from .type_and_id_parser import TypeAndIdParser
from .main import determine_type, get_inconveniences_for_everyone as get_IfE


app = FastAPI()


@app.get('/inconveniences_for_everyone')
def get_inconveniences_for_everyone():
    inconveniences = get_IfE(InconvenienceFinder())
    return inconveniences


@app.get("/inconveniences")
def get_inconveniences(name: str):
    type_ = determine_type(name)
    id_ = TypeAndIdParser().get_id(type_, name)
    inconveniences = InconvenienceFinder().get_all_inconveniences(type_, id_)
    return inconveniences
