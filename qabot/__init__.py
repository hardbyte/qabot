from typing import Optional

from qabot.config import Settings
from qabot.agent import Agent
from qabot.functions.data_loader import create_duckdb, import_into_duckdb_from_files


def ask_wikidata(query: str, verbose=False):
    agent = Agent(allow_wikidata=True, verbose=verbose)
    result = agent(query)
    return result['summary']


def ask_file(query: str, filename: Optional[str], verbose=False):
    engine = create_duckdb()
    database_engine, executed_sql = import_into_duckdb_from_files(engine, [filename])
    agent = Agent(
        database_engine=database_engine,
        verbose=verbose
    )
    result = agent(query)
    return result['summary']
