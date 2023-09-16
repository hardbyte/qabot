from typing import Optional
import httpx


class WikiDataQueryTool:
    """
    For example to select the largest cities in the world that have a female mayor, you can use the following query:

    SELECT ?cityLabel ?mayorLabel WHERE { ?city wdt:P31 wd:Q515. ?city wdt:P6 ?mayor. ?mayor wdt:P21 wd:Q6581072. ?city wdt:P1082 ?population. SERVICE wikibase:label { bd:serviceParam
    wikibase:language 'en'. } } ORDER BY DESC(?population) LIMIT 10

    Or to get billionaires:

        SELECT ?locationLabel ?item ?itemLabel (MAX(?billion) as ?billions)
        WHERE
        {
          ?item wdt:P2218 ?worth.
          ?item wdt:P19 ?location .

          FILTER(?worth>1000000000).
          BIND(?worth/1000000000 AS ?billion).
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en,de". }
        }
        GROUP BY ?locationLabel ?item ?itemLabel
        ORDER BY DESC(?billions)
        LIMIT 10

    For example to answer "How many Hospitals are there located in Beijing", you can use the following query:

        SELECT (COUNT(?hospital) AS ?count) WHERE { ?hospital wdt:P31 wd:Q16917 . ?hospital wdt:P131 wd:Q956 . SERVICE wikibase:label { bd:serviceParam wikibase:language '[AUTO_LANGUAGE],en'. } }
        LIMIT 10

    Retrieve the names of the Star Wars films:

        SELECT ?item  ?itemLabel
        WHERE
        {
          ?item wdt:P179 wd:Q22092344.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]". }
        }
    """

    name = "wikidata"
    description = """Useful for when you need specific data from Wikidata.
    Input to this tool is a single correct SPARQL statement for Wikidata. Limit all requests to 10 or fewer rows. 
    
    Output is the raw response in json. If the query is not correct, an error message will be returned. 
    If an error is returned, you may rewrite the query and try again. If you are unsure about the response
    you can try rewrite the query and try again. Prefer local data before using this tool.
    """
    base_url: str = 'https://query.wikidata.org/sparql'
    httpx_client: httpx.AsyncClient = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.httpx_client = httpx.AsyncClient()

    def _run(self, query: str) -> str:
        r = httpx.get(self.base_url, params={'format': 'json', 'query': query}, timeout=60)
        data = r.text   # no point parsing the json
        return data

    async def _arun(self, query: str) -> str:
        r = await self.httpx_client.get(self.base_url, params={'format': 'json', 'query': query}, timeout=60)
        data = r.text
        return data
