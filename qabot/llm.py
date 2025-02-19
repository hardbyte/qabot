import openai
from openai.types.chat import ChatCompletionToolParam, ChatCompletionNamedToolChoiceParam
from openai import RateLimitError, AuthenticationError, OpenAI
from rich import print
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_not_exception_type


@retry(
    retry=retry_if_not_exception_type((RateLimitError, AuthenticationError)),
    wait=wait_random_exponential(multiplier=1, max=40),
    stop=stop_after_attempt(3)
)
def chat_completion_request(
    openai_client: OpenAI,
    messages, functions=None, function_call=None, model="gpt-4o-mini"
):
    call_data = {"model": model, "messages": messages}

    if functions is not None:
        call_data["tools"] = [
            ChatCompletionToolParam(function=f, type="function") for f in functions
        ]

    if function_call is not None:
        print(f"Calling function {function_call}")
        call_data["tool_choice"] = ChatCompletionNamedToolChoiceParam(
            function=function_call,
            type='function',
        )
    try:
        return openai_client.chat.completions.create(**call_data)
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        raise e
