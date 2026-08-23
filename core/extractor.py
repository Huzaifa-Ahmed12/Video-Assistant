#ActionableItems, Decisions, Questions

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough,RunnableLambda
import os

def get_llm():
    return ChatMistralAI(model="mistral-small-latest",mistral_api_key=os.getenv("MISTRAL_API_KEY"),temperature=0.2)

def build_chain(system_prompt:str):
    llm=get_llm()
    return(
        RunnablePassthrough() | RunnableLambda(lambda x: {"text":x}) | ChatPromptTemplate.from_messages([
            ("system",system_prompt),
            ("human","{text}")
        ]) | llm | StrOutputParser()
    )

def extract_action_items(transcript:str)->str:
    chain=build_chain(
        """You are an expert meeting analyst. From the meeting transcriptons
        extract all the action items. For each provide:
        -Task Descriptions
        -Owner (Who's reponsible)
        -Deadline (if mentioned and if not mentioned dont write yourself)
        - Format these as number list and if no found give 'No Actions Found' """
    )
    return chain.invoke(transcript)

def extract_key_decisions(transcript:str)->str:
    chain=build_chain(
        """You are an expert meeting analyst. From the meeting Transcriptions 
        extract all the key decisions made. Write them all in a numbered list
        and if none found simply give 'No key Decisions Made'"""
    )
    return chain.invoke(transcript)

def extract_questions(transcript:str)->str:
    chain=build_chain(
        """You are a powerful meeting analyst. From the meeting transcript extract
        all unresolved questions and topics needing follow-up. Format them as a list
        and if no questions are there simply give 'No Questions found' """
    )
    return chain.invoke(transcript)