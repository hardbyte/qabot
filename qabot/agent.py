import json
import textwrap
from typing import Callable

from rich import print


from qabot.functions.describe_duckdb_table import describe_table_or_view
from qabot.functions.duckdb_query import run_sql_catch_error
from qabot.functions.wikidata import WikiDataQueryTool
from qabot.llm import chat_completion_request
from qabot.prompts.system import system_prompt


class Agent:
    """
    An Agent is a wrapper around a Language Model that can be used to interact with the LLM.
    Our agent also wraps the functions that can be called by the LLM.
    """

    def __init__(self,
                 database_engine=None,
                 model_name: str = 'gpt-3.5-turbo',
                 allow_wikidata: bool = False,
                 clarification_callback: Callable[[str], str] | None = None,
                 verbose=False):
        """
        Create a new Agent.
        """

        self.model_name = model_name
        self.db = database_engine
        self.verbose = verbose
        self.functions = {
            "clarify": clarification_callback,
            "wikidata": lambda query: WikiDataQueryTool()._run(query),
            "execute_sql": lambda query: run_sql_catch_error(database_engine, query),
            "show_tables": lambda: run_sql_catch_error(database_engine, "show tables"),
            "describe_table": lambda table: describe_table_or_view(database_engine, table),
        }
        self.function_specifications = [
            {
                "name": "execute_sql",
                "description": """Run SQL queries with a local DuckDB database engine. Use for accessing data or any math computation""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "DuckDB dialect SQL query. Check the table exists first.",
                        },
                    },
                    "required": ["query"],
                }
            },
            {
                "name": "show_tables",
                "description": "Show the locally available database tables and views",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "describe_table",
                "description": "Show the column names and types of a local database table or view",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "description": "The table or view name",
                        },
                    },
                    "required": ["table"],
                },
            },
            # A special function to call to summarize the answer
            {
                "name": "answer",
                "description": "Final reply to the user question with a detailed fact based answer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "A standalone one-line summary answering the users question",
                        },
                        "detail": {
                            "type": "string",
                            "description": "detailed answer to the users question including how it was computed. Markdown is acceptable",
                        },
                        "query": {
                            "type": "string",
                            "description": "If the user can re-run the query, include it here",
                        },
                        # "value": {
                        #     "type": "any",
                        #     "description": "If the answer is a number or array, include the value here",
                        # }
                    },
                    "required": ["summary", "detail"],
                },
            },

        ]

        if allow_wikidata:
            self.function_specifications.append(
                {
                    "name": "wikidata",
                    "description": textwrap.dedent(
                        """Useful for when you need specific data from Wikidata.
                        Input to this tool is a single correct SPARQL statement for Wikidata. Limit all requests to 10 or fewer rows. 

                        Output is the raw response in json. If the query is not correct, an error message will be returned. 
                        If an error is returned, you may rewrite the query and try again. If you are unsure about the response
                        you can try rewrite the query and try again. Prefer local data before using this tool.
                        """),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "A valid SPARQL query for Wikidata",
                            },
                        }
                    }
                }
            )

        if clarification_callback is not None:
            self.function_specifications.append(
                {
                    "name": "clarify",
                    "description": textwrap.dedent(
                        """Useful for when you need to ask the user a question to clarify their request.
                        Input to this tool is a single question for the user. Output is the user's response
                        """),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "clarification": {
                                "type": "string",
                                "description": "A question or prompt for the user",
                            },
                        }
                    }
                }
            )

        messages = []

        messages.append({"role": "system",
                         "content": system_prompt})
        # messages.append({"role": "user", "content": user_prompt})

        # Let's force the assistant to get the current tables
        messages.append(
            {
                'role': 'assistant',
                'content': None,
                'function_call': {'name': 'show_tables', 'arguments': '{}'}
            }
        )
        messages.append(
            {
                "role": "function",
                "name": 'show_tables',
                "content": execute_function_call(messages[-1], self.functions)
            })

        self.messages = messages

    def __call__(self, user_input):
        """
        Pass new input from the user to the LLM and return the response.
        """
        return self.run(user_input)

    def run(self, user_input):
        """
        Run the LLM/function execution loop and return the final response.
        """
        self.messages.append(
            {
                "role": "user",
                "content": user_input
            })

        for _ in range(50):
            chat_response = chat_completion_request(
                self.messages,
                functions=self.function_specifications,
                model=self.model_name
            )

            #print("Raw output")
            #print(chat_response)

            message = chat_response.choices[0]['message']
            self.messages.append(message)
            if 'function_call' in message:
                function_name = message["function_call"]["name"]

                results = execute_function_call(message, self.functions)
                print(f"[pink]{results}[/pink]")
                if function_name == 'answer':
                    return results

                else:
                    # Inject a response message for the function call
                    self.messages.append(
                        {
                            "role": "function",
                            "name": message['function_call']['name'],
                            "content": results
                        })


def create_agent_executor(**kwargs):
    return Agent(**kwargs)


def execute_function_call(message, functions):
    function_name = message["function_call"]["name"]
    kwargs = json.loads(message["function_call"]["arguments"])
    if function_name in functions:
        f = functions[function_name]
        results = f(**kwargs)
    elif function_name == 'answer':
        return kwargs
    else:
        results = f"Error: function {message['function_call']['name']} does not exist"
    return results
