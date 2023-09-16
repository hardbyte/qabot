from rich import print


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
