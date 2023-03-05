import time
from typing import Any

from langchain.tools import BaseTool
from sqlalchemy import text

from qabot.duckdb_query import run_sql_catch_error


class DuckDBTool(BaseTool):
    name = "execute"
    description = """useful for when you need to run SQL queries against a DuckDB database."""

    database: Any = None

    def __init__(self, engine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.database = engine

    def _run(self, query: str) -> str:

        #time.sleep(2)
        #print(query)
        return run_sql_catch_error(self.database, query)


    async def _arun(self, query: str) -> str:
        raise NotImplementedError("DuckDBTool does not support async")


