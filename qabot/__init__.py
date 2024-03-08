from typing import Optional

from qabot.agent import Agent
from qabot.config import Settings
from qabot.functions.data_loader import create_duckdb, import_into_duckdb_from_files


def ask_wikidata(query: str, model_name=None, verbose=False):
    if model_name is None:
        model_name = Settings().QABOT_MODEL_NAME
    agent = Agent(allow_wikidata=True, model_name=model_name, verbose=verbose)
    result = agent(query)
    return result["summary"]


def ask_file(query: str, filename: Optional[str], model_name=None, verbose=False):
    engine = create_duckdb()
    database_engine, executed_sql = import_into_duckdb_from_files(engine, [filename])
    if model_name is None:
        model_name = Settings().QABOT_MODEL_NAME
    agent = Agent(database_engine=database_engine, model_name=model_name, verbose=verbose)
    result = agent(query)
    return result["summary"]


def ask_database(query: str, uri: str, model_name=None, verbose=False):
    engine = create_duckdb()
    if model_name is None:
        model_name = Settings().QABOT_MODEL_NAME
    database_engine, executed_sql = import_into_duckdb_from_files(engine, [uri])
    agent = Agent(database_engine=database_engine, model_name=model_name, verbose=verbose)
    result = agent(query)
    return result["summary"]
