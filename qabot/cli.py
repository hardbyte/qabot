import textwrap
from typing import List, Optional
import warnings

import langchain
import typer
from langchain.callbacks import OpenAICallbackHandler
from langchain.callbacks.base import CallbackManager
from langchain.schema import AgentAction
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.traceback import install

from qabot.caching import configure_caching
from qabot.config import Settings
from qabot.duckdb_manual_data_loader import create_duckdb_from_files
from qabot.agent import create_agent_executor

install(suppress=[typer, langchain], max_frames=5, show_locals=False)
warnings.filterwarnings("ignore")

INITIAL_NON_INTERACTIVE_PROMPT = "🚀 How can I help you explore your database?"
INITIAL_INTERACTIVE_PROMPT = "[bold green] 🚀 How can I help you explore your database?"
FOLLOW_UP_PROMPT = "[bold green] 🚀 any further questions?"
PROMPT = "[bold green] 🚀 Query"


def format_agent_action(agent_action: AgentAction, observation) -> str:
    return f"""
[red]{agent_action.tool.strip()}([/red]
  [green]{agent_action.tool_input.strip()}[/green]
[red])[/red]

[bold red]Output:[/bold red]
[blue]{observation.strip()}[/blue]
"""


class QACallback(OpenAICallbackHandler):
    def __init__(self, *args, **kwargs):
        self.progress: Progress = kwargs.pop('progress')
        self.chain_task_ids = []
        self.tool_task_id = None

        super().__init__(*args, **kwargs)

    def on_chain_start(self, serialized, inputs, **kwargs):
        self.chain_task_ids.append(self.progress.add_task(f"on chain start"))
        if isinstance(serialized, dict) and 'name' in serialized:
            self.progress.update(self.chain_task_ids[-1], description=f"[yellow]{serialized['name']}")
        elif 'agent_scratchpad' in inputs and len(inputs['agent_scratchpad']):
            self.progress.update(self.chain_task_ids[-1], description=inputs['agent_scratchpad'])

    def on_agent_action(
        self, action: AgentAction, color: Optional[str] = None, **kwargs
    ):
        """Run on agent action."""
        print(action.log)

    def on_chain_end(self, outputs, **kwargs):
        super().on_chain_end(outputs, **kwargs)
        if isinstance(outputs, dict) and 'output' in outputs:
            outputs = outputs['output']

        self.progress.update(self.chain_task_ids[-1], description=f"[yellow]{outputs}")
        self.progress.remove_task(self.chain_task_ids.pop())

    def on_llm_end(self, response, **kwargs):
        print("[yellow]On llm end")

    def on_tool_start(self, **kwargs):
        print("[yellow]On tool start")

    def on_tool_end(self, output: str, **kwargs):
        print("[yellow]On tool end")

def main(
        query: str = typer.Option("Describe the tables", '-q', '--query', prompt=INITIAL_NON_INTERACTIVE_PROMPT),
        file: Optional[List[str]] = typer.Option(None, "-f", "--file", help="File containing data to query"),
        database_uri: Optional[str] = typer.Option(None, "-d", "--database", help="Database URI (e.g. sqlite:///mydb.db)"),
        table: Optional[List[str]] = typer.Option(None, "--table", "-t", help="Limit queries to these tables (can be specified multiple times)"),
        disable_cache: bool = typer.Option(False, "--disable-cache", help="Disable caching of LLM queries"),
        verbose: bool = typer.Option(False, "-v", "--verbose"),

):
    """
    Query a database using a simple english query.

    Example:
        qabot -q "What is the average age of the people in the table?"
    """

    settings = Settings()

    # If files are given load data into local DuckDB
    database_engine = None
    if len(file) > 0:
        if isinstance(file, str):
            file = [file]
        print("[red]🦆[/red] [bold]Loading data from files...[/bold]")
        database_engine = create_duckdb_from_files(file)

    elif database_uri is None and settings.QABOT_DATABASE_URI is None:
        raise ValueError("Must provide either database_uri or one or more files to load data from")

    with Progress(
        SpinnerColumn(),
        TextColumn("[green][progress.description]{task.description}"),
        transient=False,
    ) as progress:

        callback_manager = CallbackManager(handlers=[QACallback(progress=progress)])

        if not disable_cache:
            t = progress.add_task(description="Setting up cache...", total=None)
            configure_caching(settings.QABOT_CACHE_DATABASE_URI)
            progress.remove_task(t)

        t2 = progress.add_task(description="Creating LLM agent using langchain...", total=None)

        agent = create_agent_executor(
            database_uri=database_uri or settings.QABOT_DATABASE_URI,
            database_engine=database_engine,
            tables=table,
            return_intermediate_steps=True,
            callback_manager=callback_manager,
            verbose=False
        )
        progress.remove_task(t2)

        while True:

            t = progress.add_task(description="Processing query...", total=None)
            print("[bold red]Query: [/][green]" + query)

            result = agent(query)

            progress.remove_task(t)

            # Show intermediate steps
            if verbose:
                progress.console.print("[bold red]Intermediate Steps: [/]")
                for i, (agent_action, action_input) in enumerate(result['intermediate_steps'], 1):
                    print(f"  [bold red]Step {i}[/]")
                    print(textwrap.indent(format_agent_action(agent_action, action_input), "    "))

                print()

            # Stop the progress before outputting result and prompting for input
            progress.stop()
            print()

            print("[bold red]Result:[/]\n[bold blue]" + result['output'] + "\n")

            if not Confirm.ask(FOLLOW_UP_PROMPT, default=True):
                break

            print()
            query = Prompt.ask(PROMPT)

            if query == "exit" and Confirm.ask("Are you sure you want to Quit?"):
                break

            progress.start()

def run():
    typer.run(main)


if __name__ == '__main__':
    run()