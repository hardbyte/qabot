from typing import List, Optional
from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str

    QABOT_DATABASE_URI: Optional[str] = None
    QABOT_CACHE_DATABASE_URI: AnyUrl = "duckdb:///:memory:"
    QABOT_MODEL_NAME: str = "gpt-4"
    QABOT_TABLES: Optional[List[str]] = None
    QABOT_ENABLE_WIKIDATA: bool = True
    QABOT_ENABLE_HUMAN_CLARIFICATION: bool = True
