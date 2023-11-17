from typing import Optional

from qabot.agent import Agent
from qabot.dynamic_tooling import get_tools, instantiate_tools
from qabot.tools.data_loader import create_duckdb, import_into_duckdb_from_files


def ask_wikidata(query: str, verbose=False):
    tools = get_tools(
        include_defaults=True,
        clarification_callback=input,
        include_wikidata=True,
    )
    tools = instantiate_tools(tools)
    agent = Agent(tools=tools, verbose=verbose)
    result = agent(query)
    return result["summary"]


def ask_file(query: str, filename: Optional[str], verbose=False):
    engine = create_duckdb()
    database_engine, executed_sql = import_into_duckdb_from_files(engine, [filename])

    tools = get_tools(
        include_defaults=True,
        clarification_callback=input,
    )
    tools = instantiate_tools(tools, database_engine=database_engine)

    agent = Agent(tools=tools, verbose=verbose)
    result = agent(query)
    return result["summary"]
