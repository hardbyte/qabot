from langchain import LLMChain, PromptTemplate
from langchain.agents import AgentExecutor, ZeroShotAgent

from qabot.duckdb_execute_tool import DuckDBTool


def get_duckdb_data_loader_chain(llm, database):
    tool = DuckDBTool(engine=database)

    prompt = PromptTemplate(
        input_variables=["input", "agent_scratchpad"],
        template=_DEFAULT_TEMPLATE,
    )

    llm_chain = LLMChain(llm=llm, prompt=prompt)
    tool_names = [tool.name]
    agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=tool_names)
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=[tool],
        verbose=True
    )

    return agent_executor


_DEFAULT_TEMPLATE = """Given a description of data containing a url or local path, identify the 
extension (.json, .parquet, .csv), generate an appropriate table name, generate the SQL to load the
data into a DuckDB database.

CREATE TABLE test AS SELECT * FROM 'input-file';

Use the following format:

Input: "Description of input data here"
Extension: Extension of the input data
Action: the action to take, should be one of [execute]
Action Input: "SQL Query to load data"
Final Answer: Name of table or view that was created. Along with the SQL query that was executed.

For example:

``` 
Input: "open test.parquet from the data folder"
Extension: parquet
Action: execute
Action Input: "CREATE TABLE test AS SELECT * FROM 'data/test.parquet';"
Final Answer: test

The following SQL queries were executed:
CREATE TABLE test AS SELECT * FROM 'data/test.parquet';
```

Another example:
 
```
Input: "import data/records.json as customers"
Extension: json
Action: execute
Action Input: "CREATE table customers AS SELECT * FROM 'data/records.json';"
Final Answer: customers

The following SQL queries were executed:
CREATE table customers AS SELECT * FROM 'data/records.json';
```


Another Example:

Input: "create a view of the covid data from "s3://covid19-lake/data.csv"
Extension: csv
Action: execute
Action Input: "CREATE VIEW covid AS SELECT * FROM 's3://covid19-lake/data.csv';"
Final Answer: covid


In the case of a query that returns no results, you should output a summary as your final answer:
```
Final Answer: The data has been written to a parquet file at 'data/titanic_gender_survival.parquet'
The following SQL queries were executed:
- COPY (select * from titanic) TO 'data/titanic_gender_survival.parquet' (FORMAT PARQUET);
```

Input: {input}
{agent_scratchpad}"""
