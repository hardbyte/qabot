from typing import Optional

import duckdb
import langchain
from langchain.cache import BaseCache, RETURN_VAL_TYPE
from langchain.schema import Generation


class DuckDBCache(BaseCache):
    """Cache that uses DuckDB as a backend."""

    def __init__(self, con: duckdb.DuckDBPyConnection):
        """Initialize by creating all tables."""
        self.con = con
        self._table_name = 'full_llm_cache'
        self.con.execute(f"""
        CREATE TABLE IF NOT EXISTS {self._table_name} 
        (llm TEXT, prompt TEXT, idx INTEGER, response TEXT, generation_info JSON, PRIMARY KEY (llm, prompt, idx))
        """)


    def lookup(self, prompt: str, llm_string: str) -> Optional[RETURN_VAL_TYPE]:
        """Look up based on prompt and llm_string."""
        stmt = f"""SELECT response, generation_info FROM {self._table_name} WHERE
            llm = ? AND
            prompt = ? 
        ORDER BY idx;
        """

        self.con.execute(stmt, [llm_string, prompt])

        generations = [Generation(text=row[0], generation_info=row[1]) for row in self.con.fetchall()]
        if len(generations) > 0:
            return generations
        return None

    def update(self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE) -> None:
        """Update cache based on prompt and llm_string."""
        for i, generation in enumerate(return_val):
            # Insert the item in the table

            stmt = f"""INSERT OR IGNORE INTO {self._table_name} VALUES (?, ?, ?, ?, ?)"""
            self.con.execute(stmt, [llm_string, prompt, i, generation.text, generation.generation_info])


def configure_caching(database_connection):
    langchain.llm_cache = DuckDBCache(database_connection)
