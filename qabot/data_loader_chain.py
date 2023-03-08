import os

from langchain import LLMChain, PromptTemplate
from langchain.agents import AgentExecutor, Tool, ZeroShotAgent

from qabot.tools.describe_duckdb_table import describe_table_or_view
from qabot.tools.duckdb_execute_tool import DuckDBTool


def get_duckdb_data_loader_chain(llm, database):
    tools = [
        DuckDBTool(engine=database),
        Tool(
            name="Query Inspector",
            func=lambda query: query.strip('"').strip("'"),
            description="Useful to show the query before execution. Always inspect your query before execution. Input MUST be on one line."
        ),
        Tool(
            name="Local File Inspector",
            func=lambda query: f"File '{query}' is present." if os.path.exists(query.strip()) else f"File '{query}' does not exist",
            description="Useful to check a file exists. Always use AFTER writing to a local file. Input is the file path."
        ),
        Tool(
            name="Describe Table",
            func=lambda table: describe_table_or_view(database, table),
            description="Useful to show the column names and types of a table or view. Use a valid table name as the input."
        ),
    ]

    prompt = ZeroShotAgent.create_prompt(
        tools=tools,
        prefix=prefix,
        suffix=suffix,
        input_variables=["input", "agent_scratchpad", 'table_names'],

    )

    llm_chain = LLMChain(llm=llm, prompt=prompt)
    tool_names = [tool.name for tool in tools]
    agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=tool_names)

    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True
    )

    return agent_executor


suffix = """After outputting the Action Input you never output an Observation, that will be provided to you.

List the relevant SQL queries you ran in your final answer. 

If a query fails, try to fix it  except for where the file doesn't exist.

Output a summary of your actions in your final answer. It is important that you use the exact format:

Final Answer: I have successfully created a view called 'x' from 'filename'.

Queries should be output on one line and don't use any escape characters. 

Let's go! Remember it is important that you use the exact phrase "Final Answer: " to begin your
final answer.

Question: {input}
Thought: {agent_scratchpad}"""

prefix = """Given a description of data containing a url or local path, identify the 
extension (.json, .parquet, .csv), if not provided generate an appropriate table name that 
doesn't already exist in the database, then generate and exucute the SQL to load the data
into the DuckDB database. 

Example imports:
- CREATE TABLE test AS SELECT * FROM 'input-file';
- CREATE table customers AS SELECT * FROM 'data/records.json';
- CREATE VIEW covid AS SELECT * FROM 's3://covid19-lake/data.csv';

Your output should include the name of table or view that was created. Along with any SQL queries
that were executed.
 
In the case of a query that returns no results, you should output a summary as your final answer:

You have access to the following tables/views:
{table_names}

You have access to the following tools:
"""
