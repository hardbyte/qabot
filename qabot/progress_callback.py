from typing import Any, Dict, Optional

from langchain.callbacks import OpenAICallbackHandler
from langchain.schema import AgentAction
from rich import print
from rich.progress import Progress


class QACallback(OpenAICallbackHandler):
    def __init__(self, *args, **kwargs):
        self.progress: Progress = kwargs.pop('progress')
        self.chain_task_ids = []
        self.tool_task_id = None

        super().__init__(*args, **kwargs)

    def on_chain_start(self, serialized, inputs, **kwargs):
        self.chain_task_ids.append(self.progress.add_task(f"on chain start"))

        if isinstance(serialized, dict) and 'name' in serialized:
            self.progress.update(self.chain_task_ids[-1], description=f"[yellow]{serialized['name']}")

        elif 'agent_scratchpad' in inputs and len(inputs['agent_scratchpad']):
            self.progress.update(self.chain_task_ids[-1], description=inputs['agent_scratchpad'])

    # Not particularly interesting
    # def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs):
    #     self.tool_task_id = self.progress.add_task(description=f"[yellow]Using tool: {serialized['name']}")
    #
    # def on_tool_end(self, output: str, color, observation_prefix, llm_prefix, **kwargs):
    #     if self.tool_task_id is not None:
    #         self.progress.remove_task(self.tool_task_id)
    #         self.tool_task_id = None

    def on_agent_action(
        self, action: AgentAction, color: Optional[str] = None, **kwargs
    ):
        """Run on agent requesting an action."""
        pass
        #print(f"[{color}]{action.log}[/{color}]")

    def on_chain_end(self, outputs, **kwargs):
        super().on_chain_end(outputs, **kwargs)
        if isinstance(outputs, dict) and 'text' in outputs:
            outputs = outputs['text']
            #print(f"[cyan]{outputs}")

        self.progress.update(self.chain_task_ids[-1], description=f"[yellow]Total tokens: {self.total_tokens} {outputs}")
        self.progress.remove_task(self.chain_task_ids.pop())

    def on_agent_finish(
        self, finish, color: Optional[str] = None, **kwargs
    ) -> None:
        """Run on agent end."""
        if 'output' in finish.return_values:
            print(f"[{color}]{finish.return_values['output']}[/{color}]")

    def on_llm_end(self, response, **kwargs):
        super().on_llm_end(response, **kwargs)
        # Could add tokens to database, or progress bar here

        self.progress.update(self.chain_task_ids[-1], description=f"[yellow]Total Tokens {self.total_tokens}")
