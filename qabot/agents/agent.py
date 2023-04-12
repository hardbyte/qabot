import textwrap

from langchain import LLMMathChain
from langchain.agents import Tool, initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAIChat
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.tools.human.tool import HumanInputRun

from qabot.agents.data_query_chain import get_duckdb_data_query_chain
from qabot.duckdb_query import run_sql_catch_error
from qabot.tools.describe_duckdb_table import describe_table_or_view
from qabot.tools.wikidata import WikiDataQueryTool


def create_agent_executor(
        database_engine=None,
        return_intermediate_steps=False,
        callback_manager=None,
        verbose=False,
        model_name='gpt-3.5-turbo',
        allow_human_clarification=False,
        allow_wikidata=True,
):


    llm = ChatOpenAI(
        model_name=model_name,
        temperature=0.0
    )

    #python_chain = LLMMathChain(llm=llm, verbose=False)

    db_chain = get_duckdb_data_query_chain(
        llm=llm,
        database=database_engine,
        callback_manager=callback_manager,
        verbose=verbose
    )

    tools = []
    # Tool(
    #     name="Python",
    #     func=python_chain.run,
    #     description="Useful for when you need to run a quick simulation, or answer questions about math"
    # ),

    if database_engine is not None:
        tools.extend([
            Tool(
                name="Show Tables",
                func=lambda _: run_sql_catch_error(database_engine, "show tables"),
                description="Useful to show the locally available database tables and views. Empty input required."
            ),
            Tool(
                name="Describe Table",
                func=lambda table: describe_table_or_view(database_engine, table),
                description="Useful to show the column names and types of a local database table or view. Use the table name as the input."
            ),
            Tool(
                name="Data Op",
                func=lambda query: db_chain({
                    'table_names': run_sql_catch_error(database_engine, "select table_name, table_schema from information_schema.tables;"),
                    'input': query
                }),
                description=textwrap.dedent("""Useful to interact with local data tables. 
                Input should be a natural language question containing full context including what tables and columns are relevant to the question. 
                Use only after data is present and loaded. Prefer to request small independent steps with this tool.
                """,)
            )
        ])

    if allow_human_clarification:
        tools.append(HumanInputRun())

    if allow_wikidata:
        tools.append(WikiDataQueryTool())

    memory = ConversationBufferMemory(memory_key="chat_history", output_key="output", return_messages=True)

    agent = initialize_agent(
        tools,
        llm,
        agent="chat-conversational-react-description",
        callback_manager=callback_manager,
        return_intermediate_steps=return_intermediate_steps,
        verbose=verbose,
        agent_kwargs={
            #"input_variables": ["input", 'agent_scratchpad', 'chat_history'],
            "prefix": prompt_prefix_template
            #"prompt": prompt
        },
        memory=memory
    )
    return agent


prompt_prefix_template = """You are Qabot, a large language model trained to interact with DuckDB.

Qabot is designed to be able to assist with a wide range of tasks, from answering simple questions to 
providing in-depth explorations on a wide range of topics relating to data.

Qabot answers questions by first querying for data to guide its answer. Qabot responds with clarifying
questions if the request isn't clear. Qabot first tries to use local tables before
querying wikidata.

Qabot prefers to split questions into small discrete steps, creating views of data as one action, then
selecting data from the created view to get to the final answer.

Qabot includes a list of all important SQL queries returned by Data Op in its final answers.

Qabot does NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

If the question does not seem related to the database, Qabot returns "I don't know" as the answer.

TOOLS:
------

Qabot has access to the following tools:
"""
