from langchain import LLMChain, PromptTemplate

from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser, RetryWithErrorOutputParser
import enum

from pydantic import BaseModel, Field


class Action(str, enum.Enum):
    query = "query"
    clarification = "clarification"
    unknown = "unknown"


class DecomposeQueryRequest(BaseModel):
    response: str = Field(
        description="The extracted query, clarification request, or a note explaining why the query is unrelated to the data."
    )

    action: Action = Field(
        description="The single action that should be taken. If the action is 'query', then the query field must not be empty."
    )


template = """
The original request is: 
'''
{original_query}
'''

We have an opportunity to answer some, or all of the request given a knowledge source. Your job
is to decompose the request into small easier to answer queries.

Given the context, return a query that can be answered from the context. The query can be the
same as the original, or a new query that represents a subcomponent of the overall request.

If the query does not seem related to the given data sources, return unknown as the action.

{format_instructions}

Context:
{context}

Response:
"""


llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    temperature=0,
    max_tokens=3000,
)

parser = PydanticOutputParser(pydantic_object=DecomposeQueryRequest)
retry_parser = RetryWithErrorOutputParser.from_llm(parser=parser, llm=llm)

prompt = PromptTemplate(
    template=template,
    input_variables=["original_query", "context"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
    output_parser=parser,
)

# Note: I don't think we want to use an agent, just a chain

llm_chain = LLMChain(
    llm=llm,
    prompt=prompt,
)

inputs = {
    "context": """The titanic table contains information about the passengers on the titanic.""",
    "original_query": "How many people on the titanic were male?",
}

# Need to line up the input/output keys to chain together llms

response = llm_chain.run(**inputs)
print("Inputs", inputs)
print("Raw (unparsed) output:")
print(response)

prompt_value = prompt.format_prompt(**inputs)

parsed_response: DecomposeQueryRequest = retry_parser.parse_with_prompt(
    response, prompt_value
)

print(parsed_response.action)
print(parsed_response.response)

# try with an invalid response:

# # print(prompt_value.to_string())
#
# bad_response = '{"action": "search", "query": "How many people on the titanic were male"}'
# print(retry_parser.parse_with_prompt(bad_response, prompt_value))


#
#
#
#
# tools = [
#         Tool(
#             name="Show Tables",
#             func=lambda _: "show tables;",
#             description="Useful to show the available tables and views. Input is an empty string, output is a comma separated list of tables in the database."
#         ),
#         Tool(
#             name="Check Query",
#             func=lambda query: query,
#             description="Useful to check a query is valid. Always use this tool before executing a query"
#         ),
#         Tool(
#             name="Describe Table",
#             func=lambda table: table,
#             description="Useful to show the column names and types of a table or view. Use a valid table name as the input."
#         ),
#         #DuckDBTool(engine=database),
#         Tool(name="Execute SQL", func=lambda sql: sql, description="Useful to execute a SQL query. Use a valid SQL query as the input.")
#     ]
#
# prompt = ZeroShotAgent.create_prompt(
#         tools,
#         prefix=prefix,
#         suffix=suffix,
#         input_variables=["input", "agent_scratchpad"]
#     )
#
# llm_chain = LLMChain(prompt=prompt, llm=llm)
#
# agent_scratchpad = """Action: Show Tables
# Observation: 'titanic', 'unrelated_table'
# Thought: I should look at the schema of the 'titanic' table to see what I can query.
# """
#
# # possible_next_step = """Action: Describe Table
# # Observation: The table 'titanic' has the following schema:
# # ┌─────────────┬─────────────┬
# # │ column_name │ column_type │
# # ├─────────────┼─────────────┼
# # │ PassengerId │ BIGINT      │
# # │ Survived    │ BIGINT      │
# # │ Pclass      │ BIGINT      │
# # │ Name        │ VARCHAR     │
# # │ Sex         │ VARCHAR     │
# # │ Age         │ DOUBLE      │
# # │ SibSp       │ BIGINT      │
# # │ Parch       │ BIGINT      │
# # │ Ticket      │ VARCHAR     │
# # │ Fare        │ DOUBLE      │
# # │ Cabin       │ VARCHAR     │
# # │ Embarked    │ VARCHAR     │
# # ├─────────────┴─────────────┴
# # Thought:
# # """
#
# question = """how many passengers survived by gender from the 'titanic' table.
# """
#
# result = llm_chain({'input': question, 'agent_scratchpad': agent_scratchpad})
#
# if 'text' in result:
#     print(result['text'])
#
# print()
# print(result)
# #print(llm_chain.run({'input': question, 'agent_scratchpad': {}}))
