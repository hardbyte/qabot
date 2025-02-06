import json
import textwrap
from typing import Callable, List
from pydantic import BaseModel
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionMessageParam, ChatCompletionMessageToolCallParam, ChatCompletionAssistantMessageParam,
)
from openai.types.chat.chat_completion_message_tool_call import Function
from openai import RateLimitError, OpenAI
from rich import print

from qabot.config import AgentModelConfig
from qabot.formatting import format_robot, format_duck, format_user
from qabot.functions import get_function_specifications
from qabot.functions.data_loader import import_into_duckdb_from_files
from qabot.functions.describe_duckdb_table import describe_table_or_view
from qabot.functions.duckdb_query import run_sql_catch_error
from qabot.functions.wikidata import WikiDataQueryTool
from qabot.llm import chat_completion_request
from qabot.prompts.system import system_prompt, research_prompt


class Agent:
    """
    An Agent is a wrapper around a Language Model that can be used to interact with the LLM.
    Our agent also wraps the functions that can be called by the LLM.
    """

    def __init__(
            self,
            database_engine=None,
            models: AgentModelConfig = None,
            prompt_context: str = None,
            allow_wikidata: bool = False,
            terminate_session_callback: Callable = None,
            clarification_callback: Callable[[str], str] | None = None,
            verbose=False,
            max_iterations: int = 20,
            openai_client: OpenAI = None,
    ):
        """
        Create a new Agent.
        """
        self.max_iterations = max_iterations
        self.model_name = models.default_model_name
        self.planning_model_name = models.planning_model_name
        self.db = database_engine
        self.verbose = verbose
        if verbose:
            print(
                format_robot(
                    f"Default model: {models.default_model_name}, Thinking model: {models.planning_model_name}. Max LLM/function iterations before answer {max_iterations}"
                )
            )
        self.functions = {
            "terminate_session": terminate_session_callback,
            "clarify": clarification_callback,
            "wikidata": lambda query: WikiDataQueryTool()._run(query),
            "execute_sql": lambda query: run_sql_catch_error(database_engine, query),
            "show_tables": lambda: run_sql_catch_error(database_engine,
                                                       "select table_catalog, table_schema, table_name from system.information_schema.tables where table_schema != 'information_schema';"),
            "describe_table": lambda table, **kwargs: describe_table_or_view(
                database_engine, table, **kwargs
            ),
            "research": self.research_call,
            "load_data": lambda files: "Imported with SQL:\n"
                                       + str(import_into_duckdb_from_files(database_engine, files)[1]),
        }
        self.function_specifications = get_function_specifications(allow_wikidata, allow_research=True)

        if clarification_callback is not None:
            self.function_specifications.append(
                {
                    "name": "clarify",
                    "description": textwrap.dedent(
                        """Useful for when you need to ask the user a question to clarify their request.
                        Input to this tool is a single question for the user. Output is the user's response.
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
            )

        if terminate_session_callback is not None:
            self.function_specifications.append(
                {
                    "name": "terminate_session",
                    "description": textwrap.dedent(
                        """Indicate that the user has requested the session to be terminated.
                        Prefer to clarify unclear requests or requests you cannot address rather than terminating a session immediately.
                        """
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The final short message - usually saying goodbye",
                            },
                        },
                    },
                }
            )

        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                **{"role": "system", "content": system_prompt}
            ),

            # Force the assistant to get the current tables
            ChatCompletionAssistantMessageParam(
                role="assistant",
                content='',
                tool_calls=[
                    ChatCompletionMessageToolCallParam(
                        type="function",
                        id="show_tables",
                        function=Function(name="show_tables", arguments="{}"),
                    )
                ],
            ),
        ]

        messages.append(
            ChatCompletionToolMessageParam(
                **{
                    "role": "tool",
                    "tool_call_id": "show_tables",
                    "content": execute_function_call(messages[-1]['tool_calls'][0]['function'], self.functions),
                }
            )
        )
        if prompt_context is not None:
            messages.append({"role": "user", "content": prompt_context})

        self.messages = messages

        self.openai_client = openai_client or OpenAI()

    def __call__(self, user_input):
        """
        Pass new input from the user to the LLM and return the response.
        """
        return self.run(user_input)

    def run(self, user_input):
        """
        Run the LLM/function execution loop and return the final response.
        """
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(self.max_iterations):
            is_final_answer, result = self.llm_step()

            if is_final_answer:
                return json.loads(result)

        # If we get here, we've hit the max number of iterations
        # Let's ask the LLM to summarize the errors/answer as best it can
        self.messages.extend(
            [
                {
                    "role": "system",
                    "content": "Maximum iterations reached. Summarize what you were doing and attempt to answer the users question",
                }
            ]
        )

        _, result = self.llm_step(forced_function_call={"name": "answer"})
        return result

    def llm_step(self, forced_function_call=None):
        is_final_answer = False
        function_call_results = None

        chat_response = chat_completion_request(
            self.openai_client,
            self.messages,
            functions=self.function_specifications,
            model=self.model_name,
            function_call=forced_function_call,
        )

        choice = chat_response.choices[0]
        message = choice.message
        self.messages.append(message)
        if "tool_calls" == choice.finish_reason:
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                call_id = tool_call.id

                function_call_results = execute_function_call(
                    tool_call.function, self.functions, self.verbose
                )

                # Inject a response message for the function call
                self.messages.append(
                    ChatCompletionToolMessageParam(
                        content=function_call_results, role="tool", tool_call_id=call_id
                    )
                )

                is_final_answer = function_name == "answer"

                if self.verbose:
                    format_response = (
                        format_user if function_name == "clarification" else format_duck
                    )
                    print(format_response(function_call_results))
        if message.content is not None and self.verbose:
            print(format_robot(message.content))
        return is_final_answer, function_call_results

    def research_call(self, query):
        print("Research Time")
        # Now we use the planning LLM model
        chat_response = chat_completion_request(
            self.openai_client,
            messages=[
                         ChatCompletionSystemMessageParam(
                             **{"role": "system", "content": research_prompt}
                         ),
                     ] +
                     [{"role": "system", "content": str(m)} for m in self.messages[-10:]]
                     +
                     [
                         ChatCompletionSystemMessageParam(
                             **{"role": "system", "content": "Question follows:"}
                         ),
                         {"role": "user", "content": query}
                     ],
            model=self.planning_model_name
        )

        choice = chat_response.choices[0]
        message = choice.message

        if message.content is not None and self.verbose:
            print(format_robot(message.content))

        return message.content


def create_agent_executor(**kwargs):
    return Agent(**kwargs)


def execute_function_call(function, functions, verbose=False):
    function_name = function.name
    try:
        kwargs = json.loads(function.arguments)
    except json.decoder.JSONDecodeError:
        return "Error: function arguments were not valid JSON"

    if function_name in functions:
        f = functions[function_name]
        if verbose:
            if kwargs:
                print(format_robot(function_name), kwargs)
            else:
                print(format_robot(function_name))
        try:
            return f(**kwargs)
        except SystemExit as e:
            raise SystemExit(e)
        except Exception as e:
            results = f"Error: Calling function {function_name} raised an exception.\n\n{str(e)}"
    elif function_name == "answer":
        return json.dumps(kwargs)

    else:
        return f"Error: function {function_name} does not exist"

    return results
