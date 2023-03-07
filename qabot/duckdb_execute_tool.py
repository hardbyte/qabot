import time
from typing import Any

from langchain.tools import BaseTool
from sqlalchemy import text

from qabot.duckdb_query import run_sql_catch_error


class DuckDBTool(BaseTool):
    name = "execute"
    description = """useful for when you need to run SQL queries against a DuckDB database.
    Input to this tool is a detailed and correct SQL query, output is a result from the database.
    If the query is not correct, an error message will be returned. 
    If an error is returned, rewrite the query, check the query, and try again.
    """

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


