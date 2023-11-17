import httpx


class GraphQLQueryTool:
    """
    GraphQLQueryTool is a tool for querying GraphQL endpoints.

    """

    name = "graphql"
    description = """Useful for when you need data from a Graphql API.
    Input to this tool is connection information and a valid GraphQL query.
    
    Only query information relevant to the task to limit the size of responses.
    
    Output is the raw response in json. If the query is not correct, an error message will be returned. 
    If an error is returned, you may rewrite the query and try again. If you are unsure about the response
    you can try rewrite the query and try again. Prefer local data before using this tool.
    """
    base_url: str = "https://query.wikidata.org/sparql"
    httpx_client: httpx.AsyncClient = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.httpx_client = httpx.AsyncClient()

    def run(self, query: str) -> str:
        r = httpx.get(
            self.base_url, params={"format": "json", "query": query}, timeout=60
        )
        data = r.text  # no point parsing the json
        return data

    async def arun(self, query: str) -> str:
        r = await self.httpx_client.get(
            self.base_url, params={"format": "json", "query": query}, timeout=60
        )
        data = r.text
        return data
