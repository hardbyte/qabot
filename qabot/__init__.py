from typing import Optional

from qabot.agents.agent import create_agent_executor
from qabot.duckdb_manual_data_loader import create_duckdb, import_into_duckdb_from_files


def ask_wikidata(query: str, verbose=False):
    agent = create_agent_executor(allow_wikidata=True, verbose=verbose)
    result = agent({"input": query})
    return result['output']


def ask_file(query: str, filename: Optional[str], verbose=False):
    engine = create_duckdb()
    database_engine, executed_sql = import_into_duckdb_from_files(engine, [filename])
    agent = create_agent_executor(
        database_engine=database_engine,
        verbose=verbose
    )
    result = agent({"input": query})
    return result['output']
