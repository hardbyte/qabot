import textwrap

from langchain import LLMMathChain
from langchain.agents import Tool, initialize_agent
from langchain.llms import OpenAIChat

from qabot.data_loader_chain import get_duckdb_data_loader_chain
from qabot.data_query_chain import get_duckdb_data_query_chain
from qabot.duckdb_query import run_sql_catch_error
from qabot.tools.describe_duckdb_table import describe_table_or_view


#from qabot.duckdb_documentation import get_duckdb_docs_chain


def create_agent_executor(
        database_engine=None,
        tables=None,
        return_intermediate_steps=False,
        callback_manager=None,
        verbose=False,
):

    # db_kwargs = dict(
    #     include_tables=tables,
    #     sample_rows_in_table_info=3
    # )
    # if database_engine is not None:
    #     db = SQLDatabase(database_engine, **db_kwargs)
    # elif database_uri is not None:
    #     db = SQLDatabase.from_uri(
    #         database_uri,
    #         **db_kwargs
    #     )
    # else:
    #     raise ValueError("Must provide either database_uri or database_engine")


    llm = OpenAIChat(
        model_name="gpt-3.5-turbo",
        temperature=0.0
    )


    calculator_chain = LLMMathChain(llm=llm, verbose=False)
    # db_chain = SQLDatabaseChain(llm=llm, database=db,
    #                             return_intermediate_steps=return_intermediate_steps,
    #                             verbose=False)

    db_chain = get_duckdb_data_query_chain(llm=llm, database=database_engine)


    data_loader_chain = get_duckdb_data_loader_chain(llm=llm, database=database_engine)
    #duckdb_docs_qa_chain = get_duckdb_docs_chain(llm=llm)

    tools = [
        #DuckDBTool(db),
        Tool(
            name="Calculator",
            func=calculator_chain.run,
            description="useful for when you need to answer questions about math"
        ),
        # Tool(
        #     name="DuckDB QA System",
        #     func=duckdb_docs_qa_chain.run,
        #     description="useful for when you need to answer questions about duckdb. Input should be a fully formed question."
        # ),
        Tool(
            name="Show Tables",
            func=lambda _: run_sql_catch_error(database_engine, "show tables;"),
            description="Useful to show the available tables and views. Empty input required."
        ),
        Tool(
            name="Describe Table",
            func=lambda table: describe_table_or_view(database_engine, table),
            description="Useful to show the column names and types of a table or view. Use the table name as the input."
        ),
        Tool(
            name="Data Op",
            func=db_chain.run,
            description=textwrap.dedent("""useful for when you need to operate on data and answer questions
            requiring data. Input should be in the form of a natural language question containing full context 
            including what tables and columns are relevant to the question. Use only after data is present and loaded.
            """,)
        ),
        # Tool(
        #     name="Data Loader",
        #     func=data_loader_chain.run,
        #     description="""useful for when you need to load data from a specific local or remote file.
        #     Files can be a csv, json, sqlite, or parquet.
        #     """
        # )
    ]


    agent = initialize_agent(
        tools,
        llm,
        #agent="conversational-react-description",
        agent="zero-shot-react-description",
        callback_manager=callback_manager,
        return_intermediate_steps=return_intermediate_steps,
        verbose=True,
        agent_kwargs={
            "prefix": prompt_prefix
        }
    )
    #agent.agent.llm_chain.prompt.template
    return agent


prompt_prefix = """Answer the following question as best you can by querying for data to back up
your answer. 

Refuse to delete any data, or drop tables. When answering, you MUST query the database for any data. 
Check the available tables exist first. Prefer to create views of data, then select from the view.

You have access to the following tools:
"""