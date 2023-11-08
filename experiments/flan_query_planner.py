from langchain import HuggingFaceHub, LLMChain
from langchain.agents import Tool, ZeroShotAgent

prefix = """
You are an agent designed to interact with a SQL database.

Given an input question, create a syntactically correct DuckDB query to run, then look at the results of the
query and return the answer.

Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.

You can order the results by a relevant column to return the most interesting examples in the database.

Never query for all the columns from a specific table, only ask for a the few relevant columns given the question.

You have access to tools for interacting with the database. Only use the below tools. Only use the information returned
by the below tools to construct your final answer.

You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query 
and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

If the question does not seem related to the database, just return "I don't know" as the answer.

"""

suffix = """Begin!

Question: {input}
Thought: I should look at the tables in the database to see what I can query.
{agent_scratchpad}"""

template = """Question: {question}
"""
tools = [
    Tool(
        name="Show Tables",
        func=lambda _: "show tables;",
        description="Useful to show the available tables and views. Input is an empty string, output is a comma separated list of tables in the database.",
    ),
    Tool(
        name="Check Query",
        func=lambda query: query,
        description="Useful to check a query is valid. Always use this tool before executing a query",
    ),
    Tool(
        name="Describe Table",
        func=lambda table: table,
        description="Useful to show the column names and types of a table or view. Use a valid table name as the input.",
    ),
    # DuckDBTool(engine=database),
    Tool(
        name="Execute SQL",
        func=lambda sql: sql,
        description="Useful to execute a SQL query. Use a valid SQL query as the input.",
    ),
]
prompt = ZeroShotAgent.create_prompt(
    tools, prefix=prefix, suffix=suffix, input_variables=["input", "agent_scratchpad"]
)

llm = HuggingFaceHub(
    repo_id="google/flan-t5-xxl", model_kwargs={"temperature": 0, "max_length": 4000}
)

llm_chain = LLMChain(prompt=prompt, llm=llm)

agent_scratchpad = """Action: Show Tables
Observation: 'titanic', 'unrelated_table'
Thought: I should look at the schema of the 'titanic' table to see what I can query. 
"""

# possible_next_step = """Action: Describe Table
# Observation: The table 'titanic' has the following schema:
# ┌─────────────┬─────────────┬
# │ column_name │ column_type │
# ├─────────────┼─────────────┼
# │ PassengerId │ BIGINT      │
# │ Survived    │ BIGINT      │
# │ Pclass      │ BIGINT      │
# │ Name        │ VARCHAR     │
# │ Sex         │ VARCHAR     │
# │ Age         │ DOUBLE      │
# │ SibSp       │ BIGINT      │
# │ Parch       │ BIGINT      │
# │ Ticket      │ VARCHAR     │
# │ Fare        │ DOUBLE      │
# │ Cabin       │ VARCHAR     │
# │ Embarked    │ VARCHAR     │
# ├─────────────┴─────────────┴
# Thought:
# """

question = """how many passengers survived by gender from the 'titanic' table.
"""

result = llm_chain({"input": question, "agent_scratchpad": agent_scratchpad})

if "text" in result:
    print(result["text"])

print()
print(result)
# print(llm_chain.run({'input': question, 'agent_scratchpad': {}}))
