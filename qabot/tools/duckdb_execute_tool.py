import time
from typing import Any
from rich import print
from langchain.tools import BaseTool

from qabot.duckdb_query import run_sql_catch_error


class DuckDBTool(BaseTool):
    name = "execute"
    description = """useful for when you need to run SQL queries against a DuckDB database.
    Input to this tool is a single correct SQL statement, output is the result from the database.
    If the query is not correct, an error message will be returned. 
    If an error is returned, rewrite the query, check the query, and try again.
    """

    database: Any = None

    def __init__(self, engine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.database = engine

    def _run(self, query: str) -> str:
        #
        query_result = run_sql_catch_error(self.database, query)
        print(f"[pink]{query_result}[/pink]")
        time.sleep(0.2)
        return query_result

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("DuckDBTool does not support async")


