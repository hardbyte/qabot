from typing import Optional

import httpx
from langchain.tools import BaseTool


class WikiDataQueryTool(BaseTool):

    name = "wikidata"
    description = """useful for when you need specific data from Wikidata.
    Input to this tool is a single correct SPARQL statement for Wikidata.
    Output is the raw response in json.
    If the query is not correct, an error message will be returned. 
    If an error is returned, rewrite the query and try again.
    """
    base_url: str = 'https://query.wikidata.org/sparql'
    httpx_client: httpx.AsyncClient = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.httpx_client = httpx.AsyncClient()

    def _run(self, query: str) -> str:
        r = httpx.get(self.base_url, params={'format': 'json', 'query': query})
        data = r.json()
        return data

    async def _arun(self, query: str) -> str:
        r = await self.httpx_client.get(self.base_url, params={'format': 'json', 'query': query})
        data = r.json()
        return data
