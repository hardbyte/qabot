# qabot

Query local csv files or databases with natural language queries powered by
`langchain` and `openai`.

## Quickstart

You need to set the `OPENAI_API_KEY` environment variable to your OpenAI API key, 
which you can get from [here](https://platform.openai.com/account/api-keys).

Install the `qabot` command line tool using pip/poetry:


```bash
$ poetry install qabot
```

Then run the `qabot` command with either files or a database connection string:

### Local CSV file/s

```bash
$ qabot -q "how many passengers survived by gender?" -f data/titanic.csv
🦆 Loading data from files...
Loading data/titanic.csv into table titanic...

Query: how many passengers survived by gender?
Result:
There were 233 female passengers and 109 male passengers who survived.


 🚀 any further questions? [y/n] (y): y

 🚀 Query: what was the largest family who did not survive? 
Query: what was the largest family who did not survive?
Result:
The largest family who did not survive was the Sage family, with 8 members.

 🚀 any further questions? [y/n] (y): n

```

### Existing database

Install any required drivers for your database, e.g. `pip install psycopg2-binary` for postgres.

For example to connect and query directly from the trains database in the [relational dataset repository](https://relational.fit.cvut.cz/dataset/Trains):

```bash
$ pip install mysqlclient

$ qabot -d mysql+mysqldb://guest:relational@relational.fit.cvut.cz:3306/trains -q "what are the unique load shapes of cars, what are the maximum number of cars per train?" 
Query: what are the unique load shapes of cars, what are the maximum number of cars per train?
Result:
The unique load shapes of cars are circle, diamond, hexagon, rectangle, and triangle, and the maximum number of cars per train is 3.

```


### Links
- [Python library docs](https://langchain.readthedocs.io)
- [Agent docs to talk to arbitrary apis via OpenAPI/Swagger](https://langchain.readthedocs.io/en/latest/modules/agents/agent_toolkits/openapi.html)
- [Agents/Tools to talk SQL](https://langchain.readthedocs.io/en/latest/modules/agents/agent_toolkits/sql_database.html)
- [Typescript library](https://hwchase17.github.io/langchainjs/docs/overview/)

