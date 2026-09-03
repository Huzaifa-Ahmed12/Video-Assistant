from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough,RunnableLambda
from core.vector_store import build_vector_store,load_vector_store,get_retriever
import os

def get_llm():
    return ChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0.3
    )

def format_docs(docs):
    return "\n\n".join([doc.page_content if hasattr(doc, 'page_content') else str(doc) for doc in docs])

def build_rag_chain(transcript:str)->str:
    vector_store=build_vector_store(transcript)
    retriever=get_retriever(vector_store,k=5)
    llm=get_llm()
    prompt=ChatPromptTemplate.from_messages([
        ("system",
         """You are an expert meeting assistant. Answer the questions only from the meeting transcript mentioned below.
         If answer is not in transcript, then write i could not find answer in the provided context.
         Be concise and accurate when mentioning the qoutes and mention them clearly.
         Context of the meeting transcript {context}"""
         ),
         ("human",
        "{question}"
          )
    ])

    rag_chain=(
        {"context":retriever | RunnableLambda(format_docs),
         "question":RunnablePassthrough()
         }
         | prompt | llm | StrOutputParser()
    )
    return rag_chain

def load_rag_chain():
    vector_store=load_vector_store()
    retriever=get_retriever()
    llm=get_llm()
    prompt=ChatPromptTemplate.from_messages([
            ("system",
             """You are an expert meeting assistant. Answer the questions only from the meeting transcript mentioned below.
             If answer is not in transcript, then write i could not find answer in the provided context.
             Be concise and accurate when mentioning the qoutes and mention them clearly.
             Context of the meeting transcript {context}"""
             ),
             ("human",
            "{question}"
              )
        ])
    rag_chain=(
        {"context":retriever | RunnableLambda(format_docs),
            "question":RunnablePassthrough()
            }
            | prompt | llm | StrOutputParser()
    )
    return rag_chain

def get_question(rag_chain,question:str)->str:
    print(f"Question: {question}")
    answer=rag_chain.invoke(question)
    print(f"Answer: {answer}")
    return answer

