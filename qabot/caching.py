
from sqlalchemy import Column, Integer, String, Sequence, text
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from langchain.cache import SQLAlchemyCache
import langchain

Base = declarative_base()


class FulltextLLMCache(Base):  # type: ignore
    """Table for indexed LLM Cache"""

    __tablename__ = "llm_cache_fulltext"

    id = Column(Integer, Sequence('cache_id'), primary_key=True)
    prompt = Column(String, nullable=False, index=True)
    llm = Column(String, nullable=False)

    idx = Column(Integer)

    response = Column(String)



def configure_caching(database_uri):
    engine = create_engine(database_uri)
    langchain.llm_cache = SQLAlchemyCache(engine, FulltextLLMCache)
