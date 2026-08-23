from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
import os

def get_llm():
    return ChatMistralAI(model="mistral-small-latest",mistral_api_key=os.getenv("MISTRAL_API_KEY"),temperature=0.4)

def split_transcript(transcript:str)->list:
    splitter=RecursiveCharacterTextSplitter(
        chunk_size=3500,
        chunk_overlap=200
    )
    return splitter.split_documents(transcript)

system="""You are a powerful assistant. Your job is to summarize this portion of meeting transcript concisely"""
human="{text}"

def summarize(transcript:str)->str:
    llm=get_llm()
    map_prompts=ChatPromptTemplate.from_messages([
        ("system",system),
        ("human",human)
    ])
    map_chain=map_prompts | llm | StrOutputParser()
    chunks=split_transcript(transcript)
    chunk_summarize=[map_chain.invoke({"text":chunk}) for chunk in chunks]
    combined_chunks="\n\n".join(chunk_summarize)

    combined_prompts=ChatPromptTemplate.from_messages([  # To handle the chat overlap issue
        ("system","""You are an expert meeting assistant and you job is to combine these partial transcript
        and give a final professional summary in bullet points"""
         ),
         ("human","{text}")
    ])
    combined_chain=(
        RunnablePassthrough() | RunnableLambda(lambda x:{"text":x}) | combined_prompts | llm | StrOutputParser
    )

    return combined_chain.invoke(combined_chunks)

def generate_title(transcript:str)->str:
    llm=get_llm()

    title_chain=(
        RunnablePassthrough() | RunnableLambda(lambda x;{"text":x})| 
        ChatPromptTemplate.from_messages([
            ("system","""You are a powerful meeting assistant. Your job is to generate a short professional meeting 
            title of max 8 words. And give only title nothing else"""
             )
            ("human","{text}")
        ])
    )
    return title_chain.invoke(transcript[:3000])
