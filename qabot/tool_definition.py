from dataclasses import dataclass
from typing import Callable, Optional

from pydantic import BaseModel
from openai.types import FunctionDefinition, FunctionParameters
from typing import Protocol, Optional, Any


class RunMethodProtocol(Protocol):
    def run(self, table: Optional[str] = None) -> Any:
        ...


class QabotToolDefinition(BaseModel):
    # Note the OpenAI spec already includes the name, description and the runtime parameters
    spec: FunctionDefinition

    # Any parameters required to set up the tool e.g. an auth_token, or base_url
    setup_parameters: FunctionParameters | None = None


@dataclass
class QabotTool:

    definition: QabotToolDefinition

    # non-instantiated tool implementations (Python classes)
    implementation_class: Optional[Callable] = None

    implementation: Optional[RunMethodProtocol] = None



