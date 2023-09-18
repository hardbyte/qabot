
from typing import List, Optional
import warnings

import typer
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

from qabot.config import Settings
from qabot.functions.data_loader import import_into_duckdb_from_files, create_duckdb
from qabot.agent import Agent
from qabot.formatting import format_duck, format_robot, format_user, format_rocket, ROBOT_COLOR, DUCK_COLOR, \
    format_query
from qabot.prompts import INITIAL_NON_INTERACTIVE_PROMPT, FOLLOW_UP_PROMPT

warnings.filterwarnings("ignore")

app = typer.Typer(
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=True
)



@app.command()
def main(
        query: str = typer.Option("Describe the tables", '-q', '--query', prompt=INITIAL_NON_INTERACTIVE_PROMPT),
        file: Optional[List[str]] = typer.Option(None, "-f", "--file", help="File or url containing data to load and query"),
        database_uri: Optional[str] = typer.Option(":memory:", "-d", "--database", help="DuckDB Database URI (e.g. '/tmp/qabot.duckdb')"),
        enable_wikidata: bool = typer.Option(False, "-w", "--wikidata", help='Allow querying from wikidata'),
        verbose: bool = typer.Option(False, "-v", "--verbose", help='Essentially debug output'),
):
    """
    Query a database or Wikidata using a simple natural language query.

    Example:
        qabot -q "What is the average length of song by artist 'The Beatles'?" -f data/chinook.sqlite
    """

    settings = Settings()
    executed_sql = ''
    # If files are given load data into local DuckDB
    print(format_duck("Creating local DuckDB database..."))
    database_engine = create_duckdb(database_uri)

    if len(file) > 0:
        if isinstance(file, str):
            file = [file]
        print(format_duck("Loading data..."))
        database_engine, executed_sql = import_into_duckdb_from_files(database_engine, file)
        executed_sql = '\n'.join(executed_sql)
        print(format_query(executed_sql))

    with Progress(
        SpinnerColumn(),
        TextColumn("[green][progress.description]{task.description}"),
        transient=False,
    ) as progress:

        t2 = progress.add_task(description=format_rocket("Sending query to LLM"), total=None)

        def clarification(clarification):
            progress.stop()
            return Prompt.ask(format_rocket(f"Clarification requested:\n") + format_robot(clarification))

        agent = Agent(
            database_engine=database_engine,
            verbose=verbose,
            model_name=settings.QABOT_MODEL_NAME,
            allow_wikidata=settings.QABOT_ENABLE_WIKIDATA and enable_wikidata,
            clarification_callback=clarification if settings.QABOT_ENABLE_HUMAN_CLARIFICATION else None,
        )

        progress.remove_task(t2)

        while True:

            t = progress.add_task(description="Processing query...", total=None)
            print(format_rocket("Sending query to LLM"))
            print(format_user(query))

            result = agent(query)

            progress.remove_task(t)

            #print("Total tokens", output_callback.total_tokens, f"approximate cost in USD: {openai_callback.total_cost}")

            # Stop the progress before outputting result and prompting for any more input
            progress.stop()
            print()

            if verbose:
                # Likely the users query was quite a ways back in the console history
                print(format_rocket("Question:"))
                print(format_user(query))


            print(format_robot(result['summary']))
            print()
            print(f"[{ROBOT_COLOR}]\n{result['detail']}\n")

            if 'query' in result:
                print(format_query(result['query']))

            print()
            query = Prompt.ask(FOLLOW_UP_PROMPT)

            if query.lower() in {'q', 'exit', 'quit'} and Confirm.ask("Are you sure you want to Quit?"):
                break

            progress.start()


def run():
    app()


if __name__ == '__main__':
    run()
