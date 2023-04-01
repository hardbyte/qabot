from langchain import LLMChain
from langchain.agents import AgentExecutor, Tool
from langchain.agents.chat.base import ChatAgent

from qabot.tools.duckdb_execute_tool import DuckDBTool
from qabot.duckdb_query import run_sql_catch_error
from qabot.tools.describe_duckdb_table import describe_table_or_view


def get_duckdb_data_query_chain(llm, database, callback_manager=None, verbose=False):
    tools = [
        Tool(
            name="Show Tables",
            func=lambda _: run_sql_catch_error(database, "show tables;"),
            description="Useful to show the available tables and views. Empty input required."
        ),
        Tool(
            name="Describe Table",
            func=lambda table: describe_table_or_view(database, table),
            description="Useful to show the column names and types of a table or view. Also shows the first few rows. Use a valid table name as the input."
        ),
        Tool(
            name="Query Inspector",
            func=lambda query: query.strip('"').strip("'"),
            description="Useful to show the query before execution. Always inspect your query before execution. Input MUST be on one line."
        ),
        DuckDBTool(engine=database),
    ]

    prompt = ChatAgent.create_prompt(
        tools,
        prefix=prefix,
        suffix=suffix,
        input_variables=["input", "agent_scratchpad", 'table_names'],
    )

    #llm = ChatOpenAI(temperature=0)
    # llm_chain = SimpleSequentialChain(
    #     chains=[
    #         LLMChain(llm=llm, prompt=prompt),
    #         LLMCheckerChain(llm=llm, verbose=True),
    #     ]
    # )

    llm_chain = LLMChain(llm=llm, prompt=prompt)

    tool_names = [tool.name for tool in tools]

    agent = ChatAgent(llm_chain=llm_chain, allowed_tools=tool_names,)

    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        callback_manager=callback_manager,
        verbose=verbose,
    )

    return agent_executor


suffix = """After outputting the Action Input you never output an Observation, that will be provided to you.

List the relevant SQL queries you ran in your Final Answer. If you don't want to use any tools it's 
okay to give your message as a Final Answer.

Unless explicitly told to import data, do not import external data. Data required to answer the question should already available in a table. 

If a query fails, try fix it, if the database doesn't contain the answer, or returns no results,
output a summary of your actions in your final answer, e.g., "Successfully created a view of the data"

Execute queries separately! One per action. When appropriate, use the WITH clause to modularize the query in order to make it more readable.
Leave block comments before complex parts of the query, subqueries, joins, filters, etc. to explain step by step why they are correct

Let's go!

Question: {input}
Thought: {agent_scratchpad}"""


prefix = """Given an input question, identify the relevant tables and relevant columns, then create
one single syntactically correct DuckDB query to inspect, then execute, before returning the answer. 
If the input is a valid looking SQL query selecting data or creating a view, execute it directly. 

Even if you know the answer, you MUST show you can get the answer from the database.
Inspect your query before execution.

Refuse to delete any data, or drop tables. You only execute one statement at a time. You may import data.

Example imports:
- CREATE table customers AS SELECT * FROM 'data/records.json';
- CREATE VIEW covid AS SELECT * FROM 's3://covid19-lake/data.csv';

Unless the user specifies in their question a specific number of examples to obtain, limit your
select query to returning 5 results.

Pay attention to use only the column names that you can see in the schema description. Pay attention
to which column is in which table.

You only have access to the following tables/views:
{table_names}

You have access to the following tools:
"""



# Other examples

"""

An example final answer:
```
Final Answer: There were 109 male passengers who survived.
The following SQL queries were executed to obtain the result:
- SELECT Sex, Survived FROM titanic limit 5;
- CREATE VIEW male_survivors AS SELECT * FROM titanic WHERE Sex = 'male' AND Survived = 1;
- select count(*) from male_survivors;
```


Examples:?

For example:
 
Input: "Create a names table with an id, name and email column"
Thought: "I need to execute a query to create a table called names, with an id, name and email column"
Action: execute
Action Input: "CREATE TABLE names (id INTEGER, name VARCHAR, email VARCHAR);"
Thought: "I should describe the table to make sure it was created correctly"
Action: Describe Table
Action Input: names
Final Answer: <Summary>


Errors should be returned directly:

Input: "Create a names table with an id, name and email column"
Thought: "I need to execute a query to create a table called names, with an id, name and email column"
Action: execute
Action Input: "CREATE TABLE names (id INTEGER, name VARCHAR, email VARCHAR);"
Final Answer: Error: Catalog Error: Table with name "names" already exists!


For example:
 
Input: "count the number of entries in the "addresses" table that belong to each different city filtering out cities with a count below 50"
Thought: "I need to execute a query to count the number of entries in the "addresses" table that belong to each different city filtering out cities with a count below 50"
Action: execute
Action Input: SELECT city, COUNT(*) FROM addresses GROUP BY city HAVING COUNT(*) >= 50 limit 2;
Thought: 
Final Answer:

"""