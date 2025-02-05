from typing import List, Optional
from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_BASE_URL: str | None = None
    OPENAI_API_KEY: str

    QABOT_DATABASE_URI: str | None = None
    QABOT_CACHE_DATABASE_URI: AnyUrl = "duckdb:///:memory:"
    QABOT_MODEL_NAME: str = "gpt-4o-mini"
    QABOT_TABLES: List[str] | None = None
    QABOT_ENABLE_WIKIDATA: bool = True
    QABOT_ENABLE_HUMAN_CLARIFICATION: bool = True
