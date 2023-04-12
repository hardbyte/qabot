import enum
import json
import textwrap
from typing import Optional, List

import pydantic
from langchain import LLMChain, OpenAI
from langchain.agents import AgentExecutor, Tool
from langchain.agents.chat.base import ChatAgent
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from langchain.prompts import BaseChatPromptTemplate
from langchain import SerpAPIWrapper, LLMChain
from langchain.chat_models import ChatOpenAI
from typing import List, Union
from langchain.schema import AgentAction, AgentFinish, HumanMessage, OutputParserException, BaseOutputParser
from langchain.tools import BaseTool
from langchain.output_parsers import RetryWithErrorOutputParser

from pydantic import Field, BaseModel, validator

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

    prompt = CustomPromptTemplate(
        template=template,
        tools=tools,
        # This omits the `agent_scratchpad`, `tools`, `tool_names` variables because
        # they are generated dynamically by the CustomPromptTemplate.
        input_variables=["input", "intermediate_steps", "table_names"]
    )

    class AgentWrappedOutputFixingParser(OutputFixingParser, AgentOutputParser):
        pass

    output_parser = CustomOutputParser()
    output_fixing_parser = AgentWrappedOutputFixingParser.from_llm(parser=output_parser, llm=ChatOpenAI())

    # LLM chain consisting of the LLM and a prompt
    llm_chain = LLMChain(llm=llm, prompt=prompt)

    tool_names = [tool.name for tool in tools]

    agent = LLMSingleActionAgent(
        llm_chain=llm_chain,
        output_parser=output_fixing_parser,
        stop=["\n\n"],
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

{output_instructions}

Begin! 

Question: {input}
{agent_scratchpad}
"""

output_instructions = """
Your output must be a valid JSON object with the following keys:

{
"type": the type of action to take, should be one of [{tool_names}] or "answer".
"rational": Always think about what to do. Include your plan here.
"input": The input to the action. Not required when type="answer".
"result": The final answer to the question when type="answer". Only allowed when type="answer". Should be an object with "output" and "query" keys. 
  The "output" should be a string with the Answer to the initial question. Markdown is supported. "query" should be a single string containing the SQL query used to obtain the answer.
}

Output 3 new lines after the JSON object.

Remember you must execute a query before providing an answer. The output of previous actions will be provided to you, only "answer" after querying the data.
"""


class CustomOutputParser(AgentOutputParser):
    def get_format_instructions(self) -> str:
        return output_instructions

    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:
        try:
            data = CustomLLMResponse.parse_raw(llm_output)
        except pydantic.ValidationError as e:
            print("format error", e)
            raise OutputParserException from e

        # Check if agent should finish
        if data.type == 'answer':
            if data.result and data.result.query:
                queries = 'SQL Used:\n' + data.result.query
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
    query: Optional[str] = Field(description="SQL query used")


class CustomLLMResponse(BaseModel):
    type: str = Field(description='the type of action to take, including "answer"')
    input: Optional[str] = Field(description='Input to the action. Not required when type="answer"')
    rational: str = Field(description="you should always think about what to do")
    result: Optional[CustomLLMResult] = Field(description="The result of the action. Only required when type='answer'")

    @validator("result", always=True, pre=True)
    def provide_result_only_on_answer(cls, value, values):
        if value is None and values['type'] == "answer":
            raise ValueError("result is required when type='answer'")
        elif values['type'] != "answer" and value is not None:
            raise ValueError("result is only allowed when type='answer'")
        else:
            return value


class CustomPromptTemplate(BaseChatPromptTemplate):
    # The template to use
    template: str
    # The list of tools available
    tools: List[BaseTool]

    def format_messages(self, **kwargs):
        # Get the intermediate steps (AgentAction, Observation tuples)
        # Format them in a particular way
        intermediate_steps = kwargs.pop("intermediate_steps")
        if len(intermediate_steps) == 0:
            thoughts = "Thought: I should execute a query before giving my answer\n"
        else:
            thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "

        # Set the agent_scratchpad variable to that value
        kwargs["agent_scratchpad"] = thoughts
        # Create a tools variable from the list of tools provided
        kwargs["tools"] = "\n".join([f'"{tool.name}": {tool.description}' for tool in self.tools])
        # Create a list of tool names for the tools provided
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])

        kwargs['output_instructions'] = output_instructions

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