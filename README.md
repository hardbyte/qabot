# qabot

Query local or remote files with natural language queries powered by
OpenAI's `gpt` and `duckdb` 🦆.

Can query local and remote files (CSV, parquet)

## Installation

Install with `uv`, `pipx`, `pip` etc:

```
uv tool install qabot
```

## Features

Works on local CSV, sqlite and Excel files:

![](.github/local_csv_query.png)

remote CSV files:

```
$ qabot -f https://duckdb.org/data/holdings.csv -q "Tell me how many Apple holdings I currently have"
 🦆 Creating local DuckDB database...
 🦆 Loading data...
create view 'holdings' as select * from 'https://duckdb.org/data/holdings.csv';
 🚀 Sending query to LLM
 🧑 Tell me how many Apple holdings I currently have
 🤖 You currently have 32.23 shares of Apple.


This information was obtained by summing up all the Apple ('APPL') shares in the holdings table.

SELECT SUM(shares) as total_shares FROM holdings WHERE ticker = 'APPL'
```

Even on (public) data stored in S3:

```
$ qabot -f s3://covid19-lake/enigma-jhu-timeseries/csv/jhu_csse_covid_19_timeseries_merged.csv -q "how many confirmed cases of covid are there by month?" -v

🤖 Monthly confirmed cases from January to May 2020: ranging from 7 in January, 24 in February, 188,123 in March, 1,069,172 in April and 1,745,582 in May.
```

<details>
  <summary>Extra Details (from qabot)</summary>
  
  The above figures were computed by aggregating the dataset on a per-entity basis (using a unique identifier `uid`), selecting the last available (maximum) date in each month, and summing the confirmed case counts. Here is the SQL query that was used:
  
  ```sql
  WITH monthly_data AS (
      SELECT uid, strftime('%Y-%m', date) AS month, MAX(date) AS max_date
      FROM memory.main.jhu_csse_covid_19_timeseries_merged
      GROUP BY uid, strftime('%Y-%m', date)
  )
  SELECT m.month, SUM(j.confirmed) AS confirmed
  FROM monthly_data m
  JOIN memory.main.jhu_csse_covid_19_timeseries_merged j
    ON m.uid = j.uid AND m.max_date = j.date
  GROUP BY m.month
  ORDER BY m.month;
  ```

  This method ensures that for each month, the cumulative confirmed case count is captured at the end of the month based on the latest data available for each entity (uid).
</details>


### Load data within a session

You can even load data from disk/URL via the natural language query:

> Load the file 'data/titanic.csv' into a table called 'raw_passengers'. 
> Create a view of the raw passengers table for just the male passengers. What 
> was the average fare for surviving male passengers?

```
 🦆 Creating local DuckDB database...
 🚀 Sending query to LLM
 🤖 The average fare for surviving male passengers is approximately $40.82.


I created a table called `raw_passengers` from the Titanic dataset loaded from 'data/titanic.csv'. Then, I created a view called `male_passengers` that
includes only male passengers. Finally, I calculated the average fare for surviving male passengers, which is approximately $40.82.

SELECT AVG(Fare) AS average_fare_surviving_male FROM male_passengers WHERE Survived = 1;

```

## Quickstart

You need to set the `OPENAI_API_KEY` environment variable to your OpenAI API key, 
which you can get from [here](https://platform.openai.com/account/api-keys). Other OpenAI compatible
APIs can also be used by setting `OPENAI_BASE_URL`.

Install the `qabot` command line tool using uv/pip/pipx:


```bash
$ uv tool install qabot
```

Then run the `qabot` command with optional files (`-f my-file.csv`) and an initial query `-q "How many..."`.

See all options with `qabot --help`

## Security Risks

This program gives an LLM access to your local and network accessible files and allows it to execute arbitrary SQL 
queries in a DuckDB database, see [Security](Security.md) for more information.


## LLM Providers

qabot works with any OpenAI compatible api including Ollama and deepseek. Simple set the base URL:
```
export OPENAI_BASE_URL=https://api.deepseek.com
```

Or Ollama:
```
OPENAI_BASE_URL=http://localhost:11434/v1/ 
QABOT_MODEL_NAME=qwen2.5-coder:7b 
QABOT_PLANNING_MODEL_NAME=deepseek-r1:14b 
```

## Python API

```python
from qabot import ask_wikidata, ask_file, ask_database

print(ask_wikidata("How many hospitals are there in New Zealand?"))
print(ask_file("How many men were aboard the titanic?", 'data/titanic.csv'))
print(ask_database("How many product images are there?", 'postgresql://user:password@localhost:5432/dbname'))
```

Output:
```text
There are 54 hospitals in New Zealand.
There were 577 male passengers on the Titanic.
There are 6,225 product images.
```


## Examples

### Local CSV file/s

```bash
$ qabot -q "Show the survival rate by gender, and ticket class shown as an ASCII graph" -f data/titanic.csv
🦆 Loading data from files...
Loading data/titanic.csv into table titanic...

Here’s the survival count represented as a horizontal bar graph grouped by ticket class and gender:

Class 1:
Females  | ██████████████████████████████████████████ (91)
Males    | ██████████████ (45)

Class 2:
Females  | ██████████████████████████ (70)
Males    | ██████████ (17)

Class 3:
Females  | ██████████████████████████████ (72)
Males    | ██████████████ (47)


This representation allows us to observe that in all classes, a greater number of female passengers survived compared to male passengers, and also highlights the number of survivors is notably higher in the first class compared to the other classes.
```


## Query WikiData

Use the `-w` flag to query wikidata.

```bash
$ qabot -w -q "How many Hospitals are there located in Beijing"
```

## Intermediate steps and database queries

Use the `-v` flag to see the intermediate steps and database queries.
Sometimes it takes a long route to get to the answer, but it's often interesting to see how it gets there.

## Data accessed via http/s3

Use the `-f <url>` flag to load data from a url, e.g. a csv file on s3:

```bash
$ qabot -f s3://covid19-lake/enigma-jhu-timeseries/csv/jhu_csse_covid_19_timeseries_merged.csv -q "how many confirmed cases of covid are there?" -v
🦆 Loading data from files...
create table jhu_csse_covid_19_timeseries_merged as select * from 's3://covid19-lake/enigma-jhu-timeseries/csv/jhu_csse_covid_19_timeseries_merged.csv';

Result:
264308334 confirmed cases
```

## Docker Usage

You can run `qabot` via Docker:

```bash
docker run --rm \
  -e OPENAI_API_KEY=<your_openai_api_key> \
  -v ./data:/opt
  ghcr.io/hardbyte/qabot -f /opt/titanic.csv -q "What ratio of passengers were under 30?"
```

Replace the mount path to your actual data along with replacing `your_openai_api_key`.

## Ideas
- G-Sheets via https://github.com/evidence-dev/duckdb_gsheets
- Streaming mode to output results as they come in
- token limits and better reporting of costs
- Supervisor agent - assess whether a query is "safe" to run, could ask for user confirmation to run anything that gets flagged.
- Often we can zero-shot the question and get a single query out - perhaps we try this before the MKL chain
- test each zeroshot agent individually
- Generate and pass back assumptions made to the user
- Add an optional "clarify" tool to the chain that asks the user to clarify the question
- Create a query checker tool that checks if the query looks valid and/or safe
- Inject AWS credentials into duckdb for access to private resources in S3
- Automatic publishing to pypi e.g. using [trusted publishers](https://blog.pypi.org/posts/2023-04-20-introducing-trusted-publishers/)
