import openai
from openai.types.chat import ChatCompletionToolParam
from rich import print
from tenacity import retry, wait_random_exponential, stop_after_attempt


@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(
    messages, functions=None, function_call=None, model="gpt-3.5-turbo"
):
    call_data = {"model": model, "messages": messages}

    if functions is not None:
        call_data["tools"] = [
            ChatCompletionToolParam(function=f, type="function") for f in functions
        ]

    if function_call is not None:
        call_data["function_call"] = function_call
    try:
        return openai.chat.completions.create(**call_data)
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        raise e
