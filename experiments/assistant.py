import time

from rich import print
from openai import OpenAI

from qabot import create_duckdb, import_into_duckdb_from_files
from qabot.agent import execute_function_call
from qabot.config import Settings
from qabot.download_utils import download_and_cache
from qabot.functions import get_function_specifications
from qabot.functions.describe_duckdb_table import describe_table_or_view
from qabot.functions.duckdb_query import run_sql_catch_error
from qabot.functions.wikidata import WikiDataQueryTool
from qabot.prompts.system import system_prompt

functions = {
    "wikidata": lambda query: WikiDataQueryTool()._run(query),
    "execute_sql": lambda query: run_sql_catch_error(database_engine, query),
    "show_tables": lambda: run_sql_catch_error(database_engine, "show tables"),
    "describe_table": lambda table: describe_table_or_view(
        database_engine, table
    ),
    "load_data": lambda files: "Imported with SQL:\n"
                               + str(import_into_duckdb_from_files(database_engine, files)[1]),
}

if __name__ == "__main__":

    user_prompt = """
    Work out the average number of tracks per album, then tell me which artists have produced music over the most different
    genres. Finally recommend 10 songs from different artists that cover different genres.
    In your summary please show the duckdb version used.
    """
    config = Settings()
    # Instantiate the OpenAI client using the API key from settings
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    database_engine = create_duckdb()

    import_into_duckdb_from_files(
        database_engine,
        ["data/Chinook.sqlite"],
    )

    # Download the latest docs with a local cache a file for the llm to use
    doc_url = "https://duckdb.org/duckdb-docs.pdf"
    duckdb_docs_filepath = download_and_cache(doc_url)

    docsfile = client.files.create(
        file=open(duckdb_docs_filepath, "rb"),
        purpose='assistants'
    )

    # Create an Assistant with the desired configuration
    tools = [
                # {"type": "code_interpreter"},
                {"type": "retrieval"},
            ] + [
                {"type": "function", "function": spec} for spec in
                get_function_specifications(True)
            ]

    assistant = client.beta.assistants.create(
        name="QABOT",
        instructions=system_prompt + """
        Note your tools are running on the users machine with access to their installed version
        of DuckDB, they likely have already loaded data and want you to interact with it via SQL.
        Ensure you only use paths relative to the users machine when they have asked you to.
        To be clear `/mnt/data/file-XYZ` is not a valid path for use within DuckDB tools.
        """,
        tools=tools,
        model="gpt-4-1106-preview",
        file_ids=[docsfile.id]
    )

    # Create a Thread for the conversation
    thread = client.beta.threads.create()

    # Add the user's query to the Thread
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_prompt
    )

    # Run the Assistant on the Thread
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    # Check the Run's status before retrieving results
    while run.status not in ["completed", "failed"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )

        if run.status == "requires_action":
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                # Retrieve the function name and arguments
                function_name = tool_call.function.name
                arguments = tool_call.function.arguments

                # Execute the corresponding local function
                function_call_results = execute_function_call(
                    tool_call.function, functions,
                )

                # Store the output (noting there could be multiple)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": function_call_results
                })

                if function_name == "answer":
                    print(function_call_results)

            # Submit the output of all the tools back to the run
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )

    # Retrieve and display the Assistant's response
    messages = client.beta.threads.messages.list(
        thread_id=thread.id,
        order="asc"
    )

    for message in messages:
        for text_or_image in message.content:
            if text_or_image.type == 'text':
                print(text_or_image.text.value)

    print("Completed Analysis")
