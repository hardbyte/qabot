import enum
import json
import textwrap
from typing import Optional, List

from langchain import LLMChain
from langchain.agents import AgentExecutor, Tool
from langchain.agents.chat.base import ChatAgent
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import BaseChatPromptTemplate
from langchain import SerpAPIWrapper, LLMChain
from langchain.chat_models import ChatOpenAI
from typing import List, Union
from langchain.schema import AgentAction, AgentFinish, HumanMessage
from langchain.tools import BaseTool
from pydantic import Field, BaseModel

from qabot.tools.duckdb_execute_tool import DuckDBTool
from qabot.duckdb_query import run_sql_catch_error
from qabot.tools.describe_duckdb_table import describe_table_or_view


#
# class QueryAgentResponse(BaseModel):
#     response: str = Field(
#         description="The extracted query, clarification request, or a note explaining why the query is unrelated to the data."
#     )
#
#     action: str = Field(
#         description="The single action that should be taken. If the action is 'query', then the query field must not be empty."
#     )
#
#
# parser = PydanticOutputParser(pydantic_object=QueryAgentResponse)


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

    prompt = CustomPromptTemplate(
        template=template,
        tools=tools,
        # This omits the `agent_scratchpad`, `tools`, `tool_names` variables because
        # they are generated dynamically by the CustomPromptTemplate.
        input_variables=["input", "intermediate_steps", "table_names"]
    )

    #llm = ChatOpenAI(temperature=0)
    # llm_chain = SimpleSequentialChain(
    #     chains=[
    #         LLMChain(llm=llm, prompt=prompt),
    #         LLMCheckerChain(llm=llm, verbose=True),
    #     ]
    # )

    output_parser = CustomOutputParser()


    # LLM chain consisting of the LLM and a prompt
    llm_chain = LLMChain(llm=llm, prompt=prompt)

    tool_names = [tool.name for tool in tools]

    agent = LLMSingleActionAgent(
        llm_chain=llm_chain,
        output_parser=output_parser,
        stop=["\nObservation:"],
        allowed_tools=tool_names)

    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        callback_manager=callback_manager,
        verbose=verbose,
    )

    return agent_executor



template = """Given an input question, identify the relevant tables and columns, then create
one single syntactically correct DuckDB query to inspect, then execute, before returning the answer. 

If the input is a valid looking SQL query selecting data or creating a view, execute it directly. 

Even if you know the answer, you MUST show you can get the answer from the database.
Inspect your query before execution.

Only execute one statement at a time. You may import data only if given a path. For example:
- CREATE table customers AS SELECT * FROM 'data/records.json';
- CREATE VIEW covid AS SELECT * FROM 's3://covid19-lake/data.csv';

Unless the user specifies in their question a specific number of examples to obtain, limit any
select query to returning 5 results.

Pay attention to use only the column names that you can see in the schema description. Pay attention
to which column is in which table.

The following tables/views already exist:
{table_names}

You have access to the following tools:
{tools}

List the relevant SQL queries you ran in your answer. If you don't want to use any tools it's 
okay to give your message as an answer.

Unless explicitly told to import data, do not import external data. Data required to answer the question should already available in a table. 

If a query fails, try fix it, if the database doesn't contain the answer, or returns no results,
output a summary of your actions in your final answer, e.g., "Successfully created a view of the data"

Execute queries separately! One per action. When appropriate, use the WITH clause to modularize the query in order to make it more readable.
Leave block comments before complex parts of the query, sub-queries, joins, filters, etc. to explain step by step why they are correct

Use the following format:

{output_instructions}

Begin! 

Question: {input}
{agent_scratchpad}
"""


class CustomOutputParser(AgentOutputParser):

    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:

        #data = json.loads(llm_output)
        data = CustomLLMResponse.parse_raw(llm_output)


        # Check if agent should finish
        if data.type == 'answer':
            if data.result and data.result.queries:
                queries = 'SQL Queries Used:\n' + '\n'.join(data.result.queries)
            else:
                queries = ""

            final_answer = f"""{data.result.output}\n{queries}"""

            return AgentFinish(
                return_values={'output': final_answer},
                log=llm_output,
            )

        # Parse out the action and action input
        action = data.type
        action_input = data.input or ''

        # Return the action and action input
        return AgentAction(tool=action, tool_input=action_input.strip(" ").strip('"'), log=llm_output)


class CustomLLMResult(BaseModel):

    output: str = Field(description="Answer to the initial question. Only required when type='answer'")
    queries: Optional[List] = Field(description="SQL queries used")


class CustomLLMResponse(BaseModel):
    type: str = Field(description='the type of action to take, including "answer"')
    input: Optional[str] = Field(description='Input to the action. Not required when type="answer"')
    rational: str = Field(description="you should always think about what to do")
    result: Optional[CustomLLMResult] = Field(description="The result of the action. Only required when type='answer'")


class CustomPromptTemplate(BaseChatPromptTemplate):
    # The template to use
    template: str
    # The list of tools available
    tools: List[BaseTool]

    def format_messages(self, **kwargs):
        # Get the intermediate steps (AgentAction, Observation tuples)
        # Format them in a particular way
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "

        # Set the agent_scratchpad variable to that value
        kwargs["agent_scratchpad"] = thoughts
        # Create a tools variable from the list of tools provided
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])
        # Create a list of tool names for the tools provided
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])



        kwargs['output_instructions'] = textwrap.dedent("""
            Your output should be a single valid JSON object with the following keys:
            
            {
                "type": <the type of action to take, should be one of [{tool_names}] or "answer">,
                "rational": "you should always think about what to do. Include your plan here.",
                "input": <the input to the action. Not required when type="answer">,
                "result": {
                    "output": "Answer to the initial question. Only required when type='answer'. Markdown is supported.",
                    "queries": ["SQL queries used"]
                }
            }
            """)

        # TODO probably good to get the updated table names here
        # table_names =
        formatted = self.template.format(**kwargs)
        return [
            HumanMessage(content=formatted)
        ]


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