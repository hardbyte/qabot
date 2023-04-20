import textwrap
from typing import List, Optional
import warnings

import typer
from langchain.callbacks.openai_info import OpenAICallbackHandler
from langchain.schema import AgentAction
from rich import print
from langchain.callbacks import get_callback_manager

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

from qabot.caching import configure_caching
from qabot.config import Settings
from qabot.duckdb_manual_data_loader import import_into_duckdb_from_files, create_duckdb
from qabot.agents.agent import create_agent_executor
from qabot.duckdb_query import run_sql_catch_error
from qabot.progress_callback import QACallback

warnings.filterwarnings("ignore")

INITIAL_NON_INTERACTIVE_PROMPT = "🚀 How can I help you explore your database?"
INITIAL_INTERACTIVE_PROMPT = "[bold green] 🚀 How can I help you explore your database?"
FOLLOW_UP_PROMPT = "[bold green] 🚀 anything else I can help you with?"
DUCK_PROMPT = "[bold green] 🦆"

app = typer.Typer(
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=True
)


def format_intermediate_steps(intermediate_steps):
    if isinstance(intermediate_steps, list):
        return "\n".join(intermediate_steps)
    else:
        return str(intermediate_steps)


def format_agent_action(agent_action: AgentAction, observation) -> str:
    """
    Sometimes observation is a string, sometimes it is a dict. This function handles both cases.


    """
    result = ''
    internal_result = str(observation).strip()
    logs = ''

    if isinstance(observation, dict):
        if 'input' in observation:
            # should be the same as agent_action.tool_input
            pass
        if 'output' in observation:
            internal_result = observation['output']
        #if 'intermediate_steps' in observation:
        #     observation = format_intermediate_steps(observation['intermediate_steps'])

    if len(agent_action) > 3:
        logs = '\n'.join([textwrap.indent(str(o).strip(), ' '*6) for o in agent_action])

    return f"""
[red]{agent_action.tool.strip()}[/red]
  [green]{agent_action.tool_input.strip()}[/green]

  [blue]{internal_result}[/blue]
  
    [cyan]{str(logs).strip()}[/cyan]

[bold red]{result}[/bold red]
"""


@app.command()
def main(
        query: str = typer.Option("Describe the tables", '-q', '--query', prompt=INITIAL_NON_INTERACTIVE_PROMPT),
        file: Optional[List[str]] = typer.Option(None, "-f", "--file", help="File or url containing data to query"),
        database_uri: Optional[str] = typer.Option(":memory:", "-d", "--database", help="DuckDB Database URI (e.g. '/tmp/qabot.duckdb')"),
        disable_cache: bool = typer.Option(True, "--disable-cache", help="Disable caching of LLM queries"),
        enable_wikidata: bool = typer.Option(False, "-w", "--wikidata", help='Allow querying from wikidata'),
        verbose: bool = typer.Option(False, "-v", "--verbose", help='Essentially debug output'),
):
    """
    Query a database using a simple english query.

    Example:
        qabot -q "What is the average age of the people in the table?"
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

        output_callback = QACallback(progress=progress)
        openai_callback = OpenAICallbackHandler()
        callback_manager = get_callback_manager()

        callback_manager.add_handler(openai_callback)
        callback_manager.add_handler(output_callback)

        if not disable_cache:
            t = progress.add_task(description="Setting up cache...", total=None)
            configure_caching(database_engine)
            progress.remove_task(t)

        t2 = progress.add_task(description="Creating LLM agent using langchain...", total=None)

        agent = create_agent_executor(
            #database_uri=database_uri or settings.QABOT_DATABASE_URI,
            database_engine=database_engine,
            return_intermediate_steps=True,
            callback_manager=callback_manager,
            verbose=False,
            model_name=settings.QABOT_MODEL_NAME,
            allow_wikidata=settings.QABOT_ENABLE_WIKIDATA and enable_wikidata,
            allow_human_clarification=settings.QABOT_ENABLE_HUMAN_CLARIFICATION,
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

            inputs = {
                "input": query,
                #"table_names": run_sql_catch_error(database_engine, "show tables")
            }

            result = agent(inputs)

            progress.remove_task(t)

            # Show intermediate steps
            if verbose:
                progress.console.print("[bold red]Intermediate Steps: [/]")
                for i, (agent_action, action_input) in enumerate(result['intermediate_steps'], 1):
                    print(f"  [bold red]Step {i}[/]")
                    print(textwrap.indent(format_agent_action(agent_action, action_input), "    "))

                print()

            print("Total tokens", output_callback.total_tokens, f"approximate cost in USD: {openai_callback.total_cost}")

            # Stop the progress before outputting result and prompting for input
            progress.stop()
            print()

            print("[bold red]Result:[/]\n[bold blue]" + result['output'] + "\n")
            chat_history.append(result['output'])

            print()
            query = Prompt.ask(FOLLOW_UP_PROMPT)

            if query.lower() in {'q', 'exit', 'quit'} and Confirm.ask("Are you sure you want to Quit?"):
                break

            progress.start()


def run():
    app()


if __name__ == '__main__':
    run()
