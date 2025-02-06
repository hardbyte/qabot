from typing import List
from pydantic import AnyUrl, BaseModel, model_validator
from pydantic_settings import BaseSettings


class AgentModelConfig(BaseModel):
    default_model_name: str = "gpt-4o-mini"
    planning_model_name: str = 'o3-mini'


class Settings(BaseSettings):
    OPENAI_BASE_URL: str | None = None
    OPENAI_API_KEY: str

    QABOT_DATABASE_URI: str | None = None
    QABOT_CACHE_DATABASE_URI: AnyUrl = "duckdb:///:memory:"
    QABOT_MODEL_NAME: str = "gpt-4o-mini"
    QABOT_PLANNING_MODEL_NAME: str = "o3-mini"
    QABOT_TABLES: List[str] | None = None
    QABOT_ENABLE_WIKIDATA: bool = True
    QABOT_ENABLE_HUMAN_CLARIFICATION: bool = True

    agent_model: AgentModelConfig = AgentModelConfig()

    @model_validator(mode="before")
    def combine_agent_model(cls, values):
        # Build nested config from env values before other validation occurs
        values["agent_model"] = {
            "default_model_name": values.get("QABOT_MODEL_NAME", "gpt-4o-mini"),
            "planning_model_name": values.get("QABOT_PLANNING_MODEL_NAME", "o3-mini"),
        }
        return values

    class Config:
        env_prefix = ""  # if you want to avoid prefixes
