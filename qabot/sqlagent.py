from typing import Any, List, Optional

from langchain import OpenAI, SQLDatabase

from langchain.agents.agent import AgentExecutor
from langchain.agents.agent_toolkits.sql.prompt import SQL_PREFIX, SQL_SUFFIX
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.agents.mrkl.base import ZeroShotAgent
from langchain.agents.mrkl.prompt import FORMAT_INSTRUCTIONS
from langchain.callbacks.base import BaseCallbackManager, CallbackManager
from langchain.chains.llm import LLMChain
from langchain.llms.base import BaseLLM

from qabot.caching import configure_caching
from qabot.config import Settings



def create_custom_sql_agent(
    llm: BaseLLM,
    toolkit: SQLDatabaseToolkit,
    callback_manager: Optional[BaseCallbackManager] = None,
    prefix: str = SQL_PREFIX,
    suffix: str = SQL_SUFFIX,
    format_instructions: str = FORMAT_INSTRUCTIONS,
    input_variables: Optional[List[str]] = None,
    top_k: int = 10,
    verbose: bool = False,
    return_intermediate_steps=False,
    **kwargs: Any,
) -> AgentExecutor:
    """Construct a sql agent from an LLM and tools."""
    tools = toolkit.get_tools()
    prefix = prefix.format(dialect=toolkit.dialect, top_k=top_k)
    #llm_chain = MRKLChain.from_chains()


    prompt = ZeroShotAgent.create_prompt(
        tools,
        prefix=prefix,
        suffix=suffix,
        format_instructions=format_instructions,
        input_variables=input_variables,
    )
    llm_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        callback_manager=callback_manager,
    )
    tool_names = [tool.name for tool in tools]

    agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=tool_names, **kwargs)

    return AgentExecutor.from_agent_and_tools(
        agent=agent, tools=toolkit.get_tools(),
        verbose=verbose,
        return_intermediate_steps=return_intermediate_steps
    )


def create_agent_executor(
        database_uri=None,
        database_engine=None,
        tables=None,
        return_intermediate_steps=False,
        callback_manager=None,
        verbose=False):

    db_kwargs = dict(
        include_tables=tables,
        sample_rows_in_table_info=3
    )
    if database_engine is not None:
        db = SQLDatabase(database_engine, **db_kwargs)
    elif database_uri is not None:
        db = SQLDatabase.from_uri(
            database_uri,
            **db_kwargs
        )
    else:
        raise ValueError("Must provide either database_uri or database_engine")

    toolkit = SQLDatabaseToolkit(db=db)

    llm = OpenAI(temperature=0.0)

    # Not quite working yet
    # llm = OpenAIChat(
    #     model_name="gpt-3.5-turbo",
    #     temperature=0.0
    # )


    return create_custom_sql_agent(
        llm=llm,
        toolkit=toolkit,
        callback_manager=callback_manager,
        verbose=verbose,
        return_intermediate_steps=return_intermediate_steps,
    )
