import textwrap

from langchain import LLMMathChain, OpenAI, SQLDatabase, SQLDatabaseChain
from langchain.agents import Tool, initialize_agent

from qabot.data_loader_chain import get_duckdb_data_loader_chain


def create_agent_executor(
        database_uri=None,
        database_engine=None,
        tables=None,
        return_intermediate_steps=False,
        callback_manager=None,
        verbose=False
):

    db_kwargs = dict(
        include_tables=tables,
        sample_rows_in_table_info=3
    )
    if database_engine is not None:
        db = SQLDatabase(database_engine, **db_kwargs)
    elif database_uri is not None:
        db = SQLDatabase.from_uri(
            database_uri,
            **db_kwargs
        )
    else:
        raise ValueError("Must provide either database_uri or database_engine")


    # Not quite working yet
    # llm = OpenAIChat(
    #     model_name="gpt-3.5-turbo",
    #     temperature=0.0
    # )

    llm = OpenAI(temperature=0.0)

    calculator_chain = LLMMathChain(llm=llm, verbose=False)
    db_chain = SQLDatabaseChain(llm=llm, database=db, verbose=True)

    data_loader_chain = get_duckdb_data_loader_chain(llm=llm, database=database_engine)

    tools = [
        #DuckDBTool(db),
        Tool(
            name="Calculator",
            func=calculator_chain.run,
            description="useful for when you need to answer questions about math"
        ),
        Tool(
            name="Data Lookup",
            func=db_chain.run,
            description=textwrap.dedent("""useful for when you need to answer questions requiring data. 
            Input should be in the form of a natural language question containing full context.
            
            """)
        ),
        Tool(
            name="Data Loader",
            func=data_loader_chain.run,
            description="useful for when you need to load data from a local or remote file. Files can be csv, json, sqlite, or parquet."
        )
    ]

    return initialize_agent(
        tools,
        llm,
        agent="zero-shot-react-description",
        callback_manager=callback_manager,
        return_intermediate_steps=return_intermediate_steps,
        #verbose=True
    )
