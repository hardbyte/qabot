import openai
from rich import print

from qabot import create_duckdb, import_into_duckdb_from_files
from qabot.agent import execute_function_call, create_agent_executor, Agent
from qabot.config import Settings
from qabot.formatting import pretty_print_conversation
from qabot.functions.duckdb_query import run_sql_catch_error
from qabot.functions.describe_duckdb_table import describe_table_or_view
from qabot.llm import chat_completion_request
from qabot.prompts.system import system_prompt


if __name__ == '__main__':
    user_prompt = "Work out the average number of tracks per album"
    #user_prompt = "Which artists have produced music over the longest time"

    config = Settings()
    openai.api_key = config.OPENAI_API_KEY

    database_engine = create_duckdb()

    import_into_duckdb_from_files(database_engine, [
        'data/Chinook.sqlite',
    ])

    agent = Agent(
        database_engine,
        model_name=config.QABOT_MODEL_NAME
    )

    pretty_print_conversation(agent.messages)

    results = agent(user_prompt)

    print("Completed Analysis")
    print(f"[blue]{results['summary']}[/blue]")
    print(f"[blue]{results['detail']}[/blue]")
    if 'query' in results:
        print(f"[blue]{results['query']}[/blue]")
