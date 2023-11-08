import openai
from rich import print

from qabot import create_duckdb, import_into_duckdb_from_files
from qabot.agent import Agent
from qabot.config import Settings
from qabot.formatting import pretty_print_conversation


if __name__ == "__main__":
    user_prompt = "Work out the average number of tracks per album"
    # user_prompt = "Which artists have produced music over the longest time"

    config = Settings()
    openai.api_key = config.OPENAI_API_KEY

    database_engine = create_duckdb()

    import_into_duckdb_from_files(
        database_engine,
        [
            "data/Chinook.sqlite",
        ],
    )

    agent = Agent(database_engine, model_name=config.QABOT_MODEL_NAME)

    pretty_print_conversation(agent.messages)

    results = agent(user_prompt)

    print("Completed Analysis")
    print(f"[blue]{results['summary']}[/blue]")
    print(f"[blue]{results['detail']}[/blue]")
    if "query" in results:
        print(f"[blue]{results['query']}[/blue]")
