from typing import Any

from langchain.tools import BaseTool
from sqlalchemy import text


class DuckDBTool(BaseTool):
    name = "execute"
    description = """useful for when you need to run SQL queries against a DuckDB database."""

    database: Any = None

    def __init__(self, engine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.database = engine

    def _run(self, query: str) -> str:
        try:
            res = self.database.execute(text(query))
            print(res)
            return res
        except Exception as e:
            return str(e)

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("Data Loader does not support async")


