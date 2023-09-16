import json
import openai
from tenacity import retry, wait_random_exponential, stop_after_attempt
from rich import print

from qabot import create_duckdb, import_into_duckdb_from_files
from qabot.config import Settings
from qabot.duckdb_query import run_sql_catch_error
from qabot.tools.describe_duckdb_table import describe_table_or_view


def pretty_print_conversation(messages):
    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
    }

    for message in messages:
        color = role_to_color[message["role"]]
        m = f"{message['role']}: {message['content']}"

        if message["role"] == "function":
            m = f"function ({message['name']}): {message['content']}"
        elif message["role"] == "assistant" and "function_call" in message:
            m = f"assistant {message['function_call']['name']}({message['function_call']['arguments']})"
        print(f"[{color}]{m}[/{color}]\n")


@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, functions=None, function_call=None, model='gpt-3.5-turbo'):
    call_data = {"model": model, "messages": messages}

    if functions is not None:
        call_data['functions'] = functions

    if function_call is not None:
        call_data['function_call'] = function_call
    try:
        return openai.ChatCompletion.create(**call_data)
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


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


if __name__ == '__main__':
    config = Settings()
    openai.api_key = config.OPENAI_API_KEY

    database_engine = create_duckdb()
    import_into_duckdb_from_files(database_engine, [
        'data/Chinook.sqlite',
    ])

    functions = {
        "execute_sql": lambda query: run_sql_catch_error(database_engine, query),
        "show_tables": lambda: run_sql_catch_error(database_engine, "show tables"),
        "describe_table": lambda table: describe_table_or_view(database_engine, table),
    }
    function_specifications = [
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

    messages = []
    system_prompt = """You are Qabot, a large language model trained to interact with DuckDB.
    Qabot is designed to be able to assist with a wide range of tasks, from answering simple questions to 
    providing in-depth explorations on a wide range of topics relating to data.
    
    Qabot answers questions by first querying for data to guide its answer. Qabot responds with clarifying
    questions if the request isn't clear. Qabot prefers to give factual answers backed by data, even
    calculations are computed by executing SQL. 
    
    Qabot prefers to split questions into small discrete steps, communicating the plan to the user at each step.
    
    Qabot does NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
    
    Unless the user specifies in their question a specific number of examples to obtain, limit any
    select query to returning 5 results.
    
    Pay attention to use only the column names that you can see in the schema description. Pay attention
    to which column is in which table.
        
    If the question does not seem related to the database, Qabot returns "I don't know" as the answer.
    """

    user_prompt = "Work out the average number of tracks per album"
    #user_prompt = "Which artists have produced music over the longest time"

    messages.append({"role": "system",
                     "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    # Let's force the assistant to get the current tables
    messages.append(
        {
            'role': 'assistant',
            'content': None,
            'function_call': {'name': 'show_tables', 'arguments': '{}'}
        }
    )
    messages.append(
        {"role": "function", "name": 'show_tables', "content": execute_function_call(messages[-1], functions)})

    pretty_print_conversation(messages)

    # Instead of while true let's just make sure we stop...
    for _ in range(50):
        chat_response = chat_completion_request(
            messages,
            functions=function_specifications,
            model=config.QABOT_MODEL_NAME
        )
        #print("Raw output")
        #print(chat_response)

        message = chat_response.choices[0]['message']
        messages.append(message)
        if 'function_call' in message:
            function_name = message["function_call"]["name"]

            print("Executing function call")
            results = execute_function_call(message, functions)
            print(f"[pink]{results}[/pink]")
            if function_name == 'answer':
                print("Completed Analysis")
                print(f"[blue]{results['summary']}[/blue]")
                print(f"[blue]{results['detail']}[/blue]")
                if 'query' in results:
                    print(f"[blue]{results['query']}[/blue]")
                break
            else:
                # Inject a response message for the function call
                messages.append({"role": "function", "name": message['function_call']['name'], "content": results})

        pretty_print_conversation([message])

        if message['role'] == 'system':
            break

    # print(chat_response)
    # reply = chat_response.choices[0]['message']['content']
    # print(reply)

"""
Could use Python type annotations and generate the JSON schema from that.

eg 
@openai_function
def get_current_weather(location: str, format: str) -> str:
    '''Get the current weather'''
    
"""
