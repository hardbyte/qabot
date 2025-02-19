from typing import List, Optional
import warnings
from openai import OpenAI
import typer
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
import httpx

from qabot.config import Settings
from qabot.functions.data_loader import import_into_duckdb_from_files, create_duckdb
from qabot.agent import Agent
from qabot.formatting import (
    format_duck,
    format_robot,
    format_user,
    format_rocket,
    ROBOT_COLOR,
    format_query,
)
from qabot.prompts import INITIAL_NON_INTERACTIVE_PROMPT, FOLLOW_UP_PROMPT

warnings.filterwarnings("ignore")

app = typer.Typer(pretty_exceptions_show_locals=False, pretty_exceptions_enable=False)


def handle_db(agent, arg: str):
    try:
        result = agent.functions["execute_sql"](query=arg)
        print(result)
    except Exception as e:
        print(f"[red]Error executing SQL: {e}[/red]")

def handle_describe(agent, arg: str):
    try:
        result = agent.functions["describe_table"](table=arg)
        print(format_duck(result))
    except Exception as e:
        print(f"[red]Error describing table: {e}[/red]")

def handle_help(agent, arg: str):
    print("Available commands:")
    print("  /db <SQL>         Execute SQL directly on DuckDB")
    print("  /help             Show this help message")
    print("  /exit             Exit the CLI")
    print("Anything else is sent to the LLM")


# Create a command registry
COMMAND_HANDLERS = {
    "db": handle_db,
    "help": handle_help,
    "exit": lambda agent, arg: exit(0),
}

@app.command()
def main(
    query: str = typer.Option(
        "Describe the tables", "-q", "--query", prompt=INITIAL_NON_INTERACTIVE_PROMPT
    ),
    file: Optional[List[str]] = typer.Option(
        None, "-f", "--file", help="File or url containing data to load and query"
    ),
    prompt_context: Optional[str] = typer.Option(
        None, "--context", help="File or url containing text data to use in the LLM prompt - e.g. describing the data"
    ),
    database_uri: Optional[str] = typer.Option(
        ":memory:",
        "-d",
        "--database",
        help="DuckDB Database URI (e.g. '/tmp/qabot.duckdb')",
    ),
    enable_wikidata: bool = typer.Option(
        False, "-w", "--wikidata", help="Allow querying from wikidata"
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Essentially debug output"
    ),
):
    """
    Query a database or Wikidata using a simple natural language query.

    Example:
        qabot -q "What is the average length of Queen songs?" -f data/Chinook.sqlite
    """

    settings = Settings()
    executed_sql = ""
    # If files are given load data into local DuckDB
    print(format_duck("Creating local DuckDB database..."))
    if enable_wikidata:
        print(format_duck("Enabling Wikidata..."))
    database_engine = create_duckdb(database_uri)

    openai_client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )

    if file and len(file) > 0:
        if isinstance(file, str):
            file = [file]
        print(format_duck("Loading data..."))
        database_engine, executed_sql = import_into_duckdb_from_files(
            database_engine, file
        )
        executed_sql = "\n".join(executed_sql)
        print(format_query(executed_sql))

    # Load the optional context data
    context_data = ""
    if prompt_context is not None:
        try:
            if prompt_context.startswith("http://") or prompt_context.startswith("https://"):
                response = httpx.get(prompt_context)
                response.raise_for_status()  # Raises an HTTPStatusError if the response status code is 4XX/5XX
                context_data = response.text
            else:
                with open(prompt_context, 'r', encoding='utf-8') as file:
                    context_data = file.read()
        except Exception as e:
            raise RuntimeError(f"Failed to load context data from {prompt_context}: {e}")

    
    with Progress(
        SpinnerColumn(),
        TextColumn("[green][progress.description]{task.description}"),
        transient=False,
    ) as progress:
        t2 = progress.add_task(
            description=format_rocket("Sending query to LLM"), total=None
        )

        def clarification(clarification):
            progress.stop()
            return Prompt.ask(
                format_rocket("Clarification requested:\n")
                + format_robot(clarification)
            )

        def terminate_session(message: str):
            progress.stop()
            print(format_robot(message))
            raise SystemExit

        agent = Agent(
            database_engine=database_engine,
            verbose=verbose,
            models=settings.agent_model,
            allow_wikidata=settings.QABOT_ENABLE_WIKIDATA and enable_wikidata,
            terminate_session_callback=terminate_session,
            clarification_callback=clarification
            if settings.QABOT_ENABLE_HUMAN_CLARIFICATION
            else None,
            prompt_context=context_data,
            openai_client=openai_client,
        )

        progress.remove_task(t2)

        while True:
            # Check if the input is a command (starts with "/")
            if query.startswith('/'):
                # Split command and arguments
                parts = query.strip().split(maxsplit=1)
                cmd = parts[0][1:]  # remove the leading '/'
                arg = parts[1] if len(parts) > 1 else ''

                handler = COMMAND_HANDLERS.get(cmd)
                # Stop progress to ensure output displays correctly
                progress.stop()
                print()
                if handler:
                    handler(agent, arg)
                else:
                    print(f"[red]Unknown command: {cmd}[/red]")

                print()
                # Prompt for next input after a command and continue to next loop iteration
                query = Prompt.ask(FOLLOW_UP_PROMPT)
                if query.lower() in {'n', 'no', 'q', 'exit', 'quit'}:
                    break
                #progress.start()
                continue

            print(format_rocket(f"Sending query to LLM ({settings.agent_model.default_model_name})"))
            print(format_user(query))

            t = progress.add_task(description="Processing query...", total=None)
            result = agent(query)

            # Stop the progress before outputting result and prompting for any more input
            progress.remove_task(t)
            progress.stop()
            print()


            if verbose:
                # Likely the users query was quite a ways back in the console history
                print(format_rocket("Question:"))
                print(format_user(query))

            if result:
                print(format_robot(result["summary"]))
                print()
                if "detail" in result:
                    print(f"[{ROBOT_COLOR}]\n{result['detail']}\n")

                if "query" in result:
                    print(format_query(result["query"]))

            print()
            query = Prompt.ask(FOLLOW_UP_PROMPT)

            if query.lower() in {'n', 'no', "q", "exit", "quit"}:
                #  and Confirm.ask(
                #                 "Are you sure you want to Quit?"
                #             )
                break

            progress.start()


def run():
    app()


if __name__ == "__main__":
    run()
