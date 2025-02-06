import textwrap


def get_function_specifications(allow_wikidata: bool = True):
    function_specifications = [
        {
            "name": "execute_sql",
            "description": """Run SQL queries with a local DuckDB database engine. Use for accessing data, COPYing to/from files or any math computation. 
            For best results, pass in the fully qualified name: 'table_catalog.table_schema.table_name'
            
            DuckDB functions that may be helpful:
            - SELECT size, parse_path(filename), content FROM read_text('*.md') 
            - SELECT format('I''d rather be {1} than {0}.', 'right', 'happy'); -- I'd rather be happy than right.
            - SELECT list_transform([1, 2, NULL, 3], x -> x + 1); -- [2, 3, NULL, 4]
            - SELECT list_transform([5, NULL, 6], x -> coalesce(x, 0) + 1); -- [6, 1, 7]
            - SELECT * FROM duckdb_functions()
            
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "DuckDB dialect SQL query. Check the table exists first.",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "show_tables",
            "description": "Show the locally available database tables and views",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "describe_table",
            "description": "Show the column names and types of a local database table or view.",
            "parameters": {
                "type": "object",
                "properties": {
                    "catalog": {
                        "type": "string",
                        "description": "The catalog if known e.g. 'postgres_db'.",
                    },
                    "schema": {
                        "type": "string",
                        "description": "The schema (if known)",
                    },
                    "table": {
                        "type": "string",
                        "description": "The table or view name",
                    },
                },
                "required": ["table"],
            },
        },
        {
            "name": "load_data",
            "description": "Load data from one or more local or remote files into the local DuckDB database",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "description": "File path or urls",
                        "items": {
                            "type": "string",
                            "examples": [
                                "data/chinook.sqlite",
                                "https://duckdb.org/data/prices.csv",
                            ],
                        },
                    },
                },
                "required": ["file"],
            },
        },
        # A special function to call to summarize the answer
        {
            "name": "answer",
            "description": "Reply to the user question with a detailed answer",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A standalone one-line summary answering the users question or briefly explaining why the question can't be answered",
                    },
                    "detail": {
                        "type": "string",
                        "description": """detailed answer to the user's question including how it was computed. 
                        Markdown is acceptable including code snippets and mermaid diagrams.""",
                    },
                    "query": {
                        "type": "string",
                        "description": "If the query is reproducible, include it here. Don't include the full schema",
                    },
                    # "value": {
                    #     "type": "any",
                    #     "description": "If the answer is a number or array, include the value here",
                    # }
                },
                "required": ["summary", "detail"],
            },
        },
    ]

    if allow_wikidata:
        function_specifications.append(
            {
                "name": "wikidata",
                "description": textwrap.dedent(
                    """Source data from Wikidata if not available locally.
                    Input to this tool is a single SPARQL statement for Wikidata. Limit all requests to 50 or fewer rows. 

                    Output is the raw response in json. If the query is not correct, an error message will be returned. 
                    If an error is returned, you may rewrite the query and try again. If you are unsure about the response
                    you can try rewrite the query and try again. Prefer local data before using this tool.
                    """
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "A valid SPARQL query for Wikidata",
                        },
                    },
                },
            }
        )

    return function_specifications