import json
import textwrap
from typing import Callable, List

from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionMessageParam, ChatCompletionMessageToolCallParam, ChatCompletionAssistantMessageParam,
)
from openai.types.chat.chat_completion_message_tool_call import Function

from rich import print

from qabot.formatting import format_robot, format_duck, format_user
from qabot.dynamic_tooling import get_tools, instantiate_tools

from qabot.llm import chat_completion_request
from qabot.prompts.system import system_prompt
from qabot.tool_definition import QabotTool


class Agent:
    """
    An Agent is a wrapper around a Language Model that can be used to interact with the LLM.
    Our agent also wraps the functions that can be called by the LLM.
    """

    def __init__(
        self,
        database_engine=None,
        model_name: str = "gpt-3.5-turbo",
        tools: dict[str, QabotTool] = None,
        verbose=False,
        max_iterations: int = 20,
    ):
        """
        Create a new Agent.
        """
        self.max_iterations = max_iterations
        self.model_name = model_name
        self.db = database_engine
        self.verbose = verbose
        if verbose:
            print(
                format_robot(
                    f"Using model: {model_name}. Max LLM/function iterations before answer {max_iterations}"
                )
            )

        self.tools = tools

        #     "load_data": lambda files: "Imported with SQL:\n"
        #     + str(import_into_duckdb_from_files(database_engine, files)[1]),
        # }


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
                    "content": execute_tool_call(
                        messages[-1]['tool_calls'][0]['function'],
                        self.tools
                    ),
                }
            )
        )

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
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(self.max_iterations):
            is_final_answer, result = self.llm_step()

            if is_final_answer:
                if isinstance(result, str):
                    try:
                        return json.loads(result)
                    except json.decoder.JSONDecodeError:
                        return result
                elif isinstance(result, dict):
                    return result
                else:
                    return str(result)
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
            self.messages,
            functions=[tool.definition.spec for tool in self.tools.values()],
            model=self.model_name,
            function_call=forced_function_call,
        )
        # chat_response.response.raise_for_status()

        choice = chat_response.choices[0]
        message = choice.message
        self.messages.append(message)
        if "tool_calls" == choice.finish_reason:
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                call_id = tool_call.id

                function_call_results = execute_tool_call(
                    tool_call.function, self.tools, self.verbose
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


def create_agent_executor(**kwargs):
    return Agent(**kwargs)


def execute_tool_call(tool_call, tools: dict[str, QabotTool], verbose=False):
    tool_name = tool_call.name
    try:
        kwargs = json.loads(tool_call.arguments)
    except json.decoder.JSONDecodeError:
        return "Error: function arguments were not valid JSON"

    if tool_name == "answer":
        return json.dumps(kwargs)

    if tool_name in tools:
        tool = tools[tool_name]
        if verbose:
            if kwargs:
                print(format_robot(tool_name), kwargs)
            else:
                print(format_robot(tool_name))
        if tool.implementation is None:
            return "Error: tool not implemented"
        try:
            results = tool.implementation.run(**kwargs)
        except Exception as e:
            results = f"Error: Calling function {tool_name} raised an exception.\n\n{str(e)}"

    else:
        return f"Error: function {tool_name} does not exist"

    return results
    # return ChatCompletionToolMessageParam(content=results, role='tool', tool_call_id=call_id)
