import textwrap
from typing import Callable

from qabot.tool_definition import QabotToolDefinition, QabotTool
from qabot.tools.describe_duckdb_table import DescribeTableTool
from qabot.tools.duckdb_query import ExecuteSqlTool
from qabot.tools.wikidata import WikiDataQueryTool


def get_tools(
        include_defaults: bool = True,
        clarification_callback: Callable = None,
        include_wikidata: bool = True,
        include_graphql: bool = False,
) -> dict[str, QabotTool]:
    tools = {}

    if include_defaults:
        tools["execute_sql"] = QabotTool(
            definition=QabotToolDefinition(**{

                "setup_parameters": {
                    "type": "object",
                    "properties": {
                        "database_engine": {
                            "description": "DuckDB Connection",
                        },
                    },
                    "required": ["database_engine"],
                },
                'spec': {
                    "name": "execute_sql",
                    "description": """Run SQL queries with a local DuckDB database engine. Use for accessing data, COPYing to/from files or any math computation. """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "DuckDB dialect SQL query. Check the table exists first.",
                            },
                        },
                        "required": ["query"],
                    },
                }
            }),
            implementation_class=ExecuteSqlTool
        )

        tools["show_tables"] = QabotTool(
            implementation_class=ExecuteSqlTool,
            definition=QabotToolDefinition(**{

                "setup_parameters": {
                    "type": "object",
                    "properties": {
                        "database_engine": {
                            "description": "DuckDB Connection",
                        },
                        "query": {
                            "const": "show tables"
                        }
                    },
                    "required": ["database_engine"],
                },
                'spec': {
                    "name": "show_tables",
                    "description": "Show the locally available database tables and views",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                }})
        )

        tools["describe_table"] = QabotTool(
            implementation_class=DescribeTableTool,
            definition=QabotToolDefinition(**{
                "setup_parameters": {
                    "type": "object",
                    "properties": {
                        "database_engine": {
                            "description": "DuckDB Connection",
                        }
                    },
                    "required": ["database_engine"],
                },
                'spec': {
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
                }})
        )

        # tools["load_data"] = QabotTool(**{
        #     'spec': {
        #         "name": "load_data",
        #         "description": "Load data from one or more local or remote files into the local DuckDB database",
        #         "parameters": {
        #             "type": "object",
        #             "properties": {
        #                 "files": {
        #                     "type": "array",
        #                     "description": "File path or urls",
        #                     "items": {
        #                         "type": "string",
        #                         "examples": [
        #                             "data/chinook.sqlite",
        #                             "https://duckdb.org/data/prices.csv",
        #                         ],
        #                     },
        #                 },
        #             },
        #             "required": ["file"],
        #         },
        #     }})

        # A special function to call to summarize the answer
        tools["answer"] = QabotTool(
            definition=QabotToolDefinition(**{
                'spec': {
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
                }})
        )

    if include_wikidata:
        tools["wikidata"] = QabotTool(
            implementation_class=WikiDataQueryTool,
            definition=QabotToolDefinition(**{
                'spec': {
                    "name": "wikidata",
                    "description": textwrap.dedent(
                        """Useful for when you need specific data from Wikidata.
                        Input to this tool is a single correct SPARQL statement for Wikidata. Limit all requests to 10 or fewer rows. 
    
                        Output is the raw response in json. If the query is not correct, an error message will be returned. 
                        If an error is returned, you may rewrite the query and try again. If you are unsure about the response
                        you can try rewrite the query and try again. Prefer local data before using this tool.
                        """
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "A valid SPARQL query for Wikidata",
                            },
                        },
                    },
                }})
        )

    if clarification_callback is not None:
        tools["clarify"] = QabotTool(
            implementation=clarification_callback,
            definition=QabotToolDefinition(**{
                'spec': {
                    "name": "clarify",
                    "description": textwrap.dedent(
                        """Useful for when you need to ask the user a question to clarify their request.
                        Input to this tool is a single question for the user. Output is the user's response
                        """
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "clarification": {
                                "type": "string",
                                "description": "A question or prompt for the user",
                            },
                        },
                    },
                }
            }))

    return tools


def instantiate_tools(
        tools: dict[str, QabotTool],
        **kwargs
) -> dict[str, QabotTool]:
    for tool_name in tools:
        tool = tools[tool_name]
        if tool.implementation is None and tool.implementation_class is not None:
            tool_kwargs = {}
            if tool.definition.setup_parameters is not None:
                for param_name, param_definition in tool.definition.setup_parameters.get('properties', {}).items():
                    # Could be const provided in the definition, passed in kwargs, or None
                    param_value = param_definition.get('const', kwargs.get(param_name, None))
                    tool_kwargs[param_name] = param_value
            tool.implementation = tool.implementation_class(**tool_kwargs)
        else:
            print(f"tool `{tool_name}` doesn't have an implementation")
    return tools
