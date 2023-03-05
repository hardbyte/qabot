from langchain import LLMChain, PromptTemplate
from langchain.agents import AgentExecutor, Tool, ZeroShotAgent

from qabot.duckdb_execute_tool import DuckDBTool
from qabot.duckdb_query import run_sql_catch_error
from qabot.tools.describe_duckdb_table import describe_table_or_view


def get_duckdb_data_query_chain(llm, database):
    tools = [
        Tool(
            name="Show Tables",
            func=lambda _: run_sql_catch_error(database, "show tables;"),
            description="Useful to show the available tables and views. Empty input required."
        ),
        Tool(
            name="Describe Table",
            func=lambda table: describe_table_or_view(database, table),
            description="Useful to show the column names and types of a table or view. Use a valid table name as the input."
        ),
        DuckDBTool(engine=database),
    ]

    # prompt = PromptTemplate(
    #     input_variables=["input", "agent_scratchpad"],
    #     template=_DEFAULT_TEMPLATE,
    # )

    prompt = ZeroShotAgent.create_prompt(
        tools,
        prefix=prefix,
        #suffix=suffix,
        input_variables=["input", "agent_scratchpad"]
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


prefix = """Given an input question, identify the relevant tables and relevant columns, then create
one or more syntactically correct DuckDB queries to run before returning the answer. If the input is
a valid looking SQL query selecting data or creating a view, execute it directly. 

Before answering, you MUST show the tables to make sure you specify the correct table.
Before answering, you MUST query the database for any data. Check the available columns and tables 
exist first. Refuse to delete any data, or drop tables.
 
Unless the user specifies in their question a specific number of examples to obtain, always limit your query
to at most 5 results. You can order the results by a relevant column to return the most interesting 
examples in the database.

Never query for all the columns from a specific table, only ask for the relevant columns given the question.

Pay attention to use only the column names that you can see in the schema description. Be careful 
to not query for columns that do not exist. Also, pay attention to which column is in which table.

Queries should be output across multiple lines for readability and don't use any escape characters. 

You always provide evidence with your final answer including the SQL queries you ran.

You have access to the following tools:
"""




# Other examples

"""Examples:?

For example:
 
Input: "Create a names table with an id, name and email column"
Thought: "I need to execute a query to create a table called names, with an id, name and email column"
Action: execute
Action Input: "CREATE TABLE names (id INTEGER, name VARCHAR, email VARCHAR);"
Thought: "I should describe the table to make sure it was created correctly"
Action: Describe Table
Action Input: names
Final Answer: 


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