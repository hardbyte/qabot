import textwrap

from langchain import LLMMathChain
from langchain.agents import Tool, create_sql_agent, initialize_agent
from langchain.llms import OpenAIChat

from qabot.agents.data_query_chain import get_duckdb_data_query_chain
from qabot.duckdb_query import run_sql_catch_error
from qabot.tools.describe_duckdb_table import describe_table_or_view


def create_agent_executor(
        database_engine=None,
        tables=None,
        return_intermediate_steps=False,
        callback_manager=None,
        verbose=False,
):


    llm = OpenAIChat(
        model_name="gpt-3.5-turbo",
        temperature=0.0
    )


    calculator_chain = LLMMathChain(llm=llm, verbose=False)

    db_chain = get_duckdb_data_query_chain(
        llm=llm,
        database=database_engine,
        callback_manager=callback_manager,
        verbose=verbose
    )

    tools = [
        Tool(
            name="Calculator",
            func=calculator_chain.run,
            description="Useful for when you need to answer questions about math"
        ),
        # Tool(
        #     name="DuckDB QA System",
        #     func=duckdb_docs_qa_chain.run,
        #     description="useful for when you need to answer questions about duckdb. Input should be a fully formed question."
        # ),
        Tool(
            name="Show Tables",
            func=lambda _: run_sql_catch_error(database_engine, "show tables"),
            description="Useful to show the available tables and views. Empty input required."
        ),
        Tool(
            name="Describe Table",
            func=lambda table: describe_table_or_view(database_engine, table),
            description="Useful to show the column names and types of a table or view. Use the table name as the input."
        ),
        Tool(
            name="Data Op",
            func=lambda input: db_chain({
                'table_names': lambda _: run_sql_catch_error(database_engine, "show tables;"),
                'input': input}),
            description=textwrap.dedent("""useful for when you need to operate on data and answer questions
            requiring data. Input should be in the form of a natural language question containing full context
            including what tables and columns are relevant to the question. Use only after data is present and loaded.
            """,)
        )
    ]

    agent = initialize_agent(
        tools,
        llm,
        #agent="conversational-react-description",
        agent="zero-shot-react-description",
        callback_manager=callback_manager,
        return_intermediate_steps=return_intermediate_steps,
        verbose=verbose,
        agent_kwargs={
            "input_variables": ["input", 'agent_scratchpad', 'table_names'],
            "prefix": prompt_prefix_template,
            "suffix": prompt_suffix
        }
    )
    #agent.agent.llm_chain.prompt.template
    return agent

prompt_suffix = """It is important that you use the exact phrase "Final Answer: <Summary>" in your final answer.

Begin!

Question: {input}
Thought: I should look at the tables in the database to see what I can query.
{agent_scratchpad}"""

prompt_prefix_template = """Answer the following question as best you can by querying for data to back up
your answer. Even if you know the answer, you MUST show you can get the answer from the database.

Refuse to delete any data, or drop tables. When answering, you MUST query the database for any data. 
Check the available tables exist first. Prefer to take single independent actions. Prefer to create views
of data as one action, then select data from the view.

It is important that you use the exact phrase "Final Answer: " in your final answer.
List all SQL queries returned by Data Op in your final answer.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

If the question does not seem related to the database, just return "I don't know" as the answer.

You have access to the following data tables:
{table_names}

Only use the below tools. You have access to the following tools:
"""