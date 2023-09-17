from rich import print

role_to_color = {
    "system": "red",
    "user": "green",
    "assistant": "blue",
    "function": "magenta",
}

ROBOT_COLOR = "blue"
DUCK_COLOR = "magenta"
QUERY_COLOR = "cyan"

ROCKET_EMOJI = "[red] 🚀"
DUCK_EMOJI = f"[{DUCK_COLOR}] 🦆"
ROBOT_EMOJI = f"[{ROBOT_COLOR}] 🤖"
USER_EMOJI = "[green] 🧑"


def format_query(msg):
    return f"[{QUERY_COLOR}]{msg}[/{QUERY_COLOR}]"


def format_robot(msg):
    return f"{ROBOT_EMOJI} {msg}[/]"


def format_user(msg):
    return f"{USER_EMOJI} {msg}[/]"


def format_duck(msg):
    return f"{DUCK_EMOJI} {msg}[/]"


def format_rocket(msg):
    return f"{ROCKET_EMOJI} {msg}[/]"


def pretty_print_conversation(messages):

    for message in messages:
        color = role_to_color[message["role"]]
        m = f"{message['role']}: {message['content']}"

        if message["role"] == "function":
            m = f"function ({message['name']}): {message['content']}"
        elif message["role"] == "assistant" and "function_call" in message:
            m = f"assistant {message['function_call']['name']}({message['function_call']['arguments']})"
        print(f"[{color}]{m}[/{color}]\n")

