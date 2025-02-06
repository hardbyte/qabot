from typing import Optional

from qabot.agent import Agent, AgentModelConfig
from qabot.config import Settings
from qabot.functions.data_loader import create_duckdb, import_into_duckdb_from_files


def ask_wikidata(query: str, model_name=None, verbose=False):
    model_config = Settings().agent_model
    if model_name is not None:
        model_config.default_model_name = model_name

    agent = Agent(allow_wikidata=True, models=model_config, verbose=verbose)
    result = agent(query)
    return result["summary"]


def ask_file(query: str, filename: Optional[str], model_name=None, verbose=False):
    engine = create_duckdb()
    database_engine, executed_sql = import_into_duckdb_from_files(engine, [filename])
    model_config = Settings().agent_model
    if model_name is not None:
        model_config.default_model_name = model_name
    agent = Agent(database_engine=database_engine, models=model_config, verbose=verbose)
    result = agent(query)
    return result["summary"]


def ask_database(query: str, uri: str, model_name=None, context=None, verbose=False):
    engine = create_duckdb()
    model_config = Settings().agent_model
    if model_name is not None:
        model_config.default_model_name = model_name
    database_engine, executed_sql = import_into_duckdb_from_files(engine, [uri])
    agent = Agent(database_engine=database_engine, models=model_config, prompt_context=context, verbose=verbose)
    result = agent(query)
    return result["summary"]
