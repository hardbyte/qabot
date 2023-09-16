
from typing import List, Optional
import warnings

import typer
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

from qabot.config import Settings
from qabot.duckdb_manual_data_loader import import_into_duckdb_from_files, create_duckdb
from qabot.agent import create_agent_executor, Agent

warnings.filterwarnings("ignore")

INITIAL_NON_INTERACTIVE_PROMPT = "🚀 How can I help you explore your database?"
INITIAL_INTERACTIVE_PROMPT = "[bold green] 🚀 How can I help you explore your database?"
FOLLOW_UP_PROMPT = "[bold green] 🚀 anything else I can help you with?"
DUCK_PROMPT = "[bold green] 🦆"

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
    database_engine = create_duckdb(database_uri)

    if len(file) > 0:
        if isinstance(file, str):
            file = [file]
        print("[red]🦆[/red] [bold]Loading data...[/bold]")
        database_engine, executed_sql = import_into_duckdb_from_files(database_engine, file)
        executed_sql = '\n'.join(executed_sql)
    else:
        print("[red]🦆[/red]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[green][progress.description]{task.description}"),
        transient=False,
    ) as progress:

        t2 = progress.add_task(description="Creating LLM agent", total=None)

        def clarification(clarification):
            progress.stop()
            return Prompt.ask(f"[bold red]Clarification requested:[/]\n[bold yellow]{clarification}")

        agent = Agent(
            database_engine=database_engine,
            verbose=False,
            model_name=settings.QABOT_MODEL_NAME,
            allow_wikidata=settings.QABOT_ENABLE_WIKIDATA and enable_wikidata,
            clarification_callback=clarification if settings.QABOT_ENABLE_HUMAN_CLARIFICATION else None,
        )

        progress.remove_task(t2)

        chat_history = [f"""
        Startup SQL Queries:
        ```
        {executed_sql}
        ```
        """]

        while True:

            t = progress.add_task(description="Processing query...", total=None)
            print("[bold red]Query: [/][green]" + query)

            inputs = query

            result = agent(inputs)

            progress.remove_task(t)

            #print("Total tokens", output_callback.total_tokens, f"approximate cost in USD: {openai_callback.total_cost}")

            # Stop the progress before outputting result and prompting for any more input
            progress.stop()
            print()

            print("[bold blue]Question:[/]\n[bold blue]" + query + "\n")
            print("[bold blue]Answer:[/]\n[bold blue]" + result['summary'] + "\n")
            print("\n[blue]" + result['detail'] + "[/blue]\n")
            if 'query' in result:
                print("[cyan]" + result['query'] + "[/cyan]\n")
            chat_history.append(result['summary'])


            print()
            query = Prompt.ask(FOLLOW_UP_PROMPT)

            if query.lower() in {'q', 'exit', 'quit'} and Confirm.ask("Are you sure you want to Quit?"):
                break

            progress.start()


def run():
    app()


if __name__ == '__main__':
    run()
