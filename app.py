
import streamlit as st
#from dotenv import load_dotenv
#import argparse
#from dataclasses import dataclass
from langchain.vectorstores.chroma import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os
import shutil

MAIN_CHROMA_PATH = "chroma/main"
MAIN_DATA_PATH = "data/main"

COMMON_STATEMENT = """참고로 본부는 중소벤처기업부를, 중기부는 중소벤처기업부를, 
                기재부는 기획재정부를, 산업부는 산업통상자원부를,  
                지방청은 지방중소벤처기업청을 의미하는 것을 알아둬.
        질문자들은 대한민국 공무원들이야. 대답은 진철하게 설명하는 방식으로 해줘."""

PROMPT_TEMPLATE = """
        {common}
        
        그리고 아래 내용에 근거해서만 답변을 해줘:

        {context}

        ---

        위 내용에 근거해서 답변을 해줘 : {question}
"""

keywords = ["언급되지 않", "언급이 없", "정보를 알 수 없", "제공할 수 없", "제공되지 않" , "알 수 없"]

# Prepare the DB.
@st.cache_data
def get_conversation_chain(_db, _model, user_question):
    # Search the DB.
    #st.write(user_question)
    if user_question.strip()[0] != '#':
        results = _db.similarity_search_with_relevance_scores(user_question, k=3)
    
        if len(results) == 0:
            st.write(f"검색 결과 : {len(results)}.")
            return
            
        if results[0][1] < 0.7:
            print(f"Unable to find matching results.")
            st.write("검색 결과 유사성이 거의 없습니다.")
            return
        
        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
        prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        prompt = prompt_template.format(common = COMMON_STATEMENT, context=context_text, question=user_question)
        print(prompt)
    
        response_text = _model.predict(prompt)
        for keyword in keywords:
            if keyword in response_text:
                st.write("다만 제 정보를 토대로 답변드리면...")
                response_text = _model.predict(COMMON_STATEMENT + \
                                       "질문은 다음과 같아 : " + \
                                       user_question)
                st.write(response_text)

                return response_text
                    
        sources = [doc.metadata.get("source", None) for doc, _score in results]
        formatted_response = f"Response: {response_text}\nSources: {sources}"
        print(formatted_response)
    
        st.write(formatted_response)
        st.write("----------- 출처 -----------")
        st.write(results)
    else:
        st.write("#에 의해 제 정보만을 토대로 답변드리겠습니다.")
        response_text = _model.predict(COMMON_STATEMENT + \
                                       "질문은 다음과 같아 : " + \
                                       user_question)
        st.write(response_text)
            
    return response_text

@st.cache_resource
def init_db():
    embedding_function = OpenAIEmbeddings()
    db = Chroma(persist_directory=MAIN_CHROMA_PATH, embedding_function=embedding_function)
    return db

@st.cache_resource
def init_model():
    model = ChatOpenAI()
    return model
    
def start(_db, _model):
    #st.set_page_config(page_title="Chat with multiple PDFs", page_icon=":books:")

    user_question = st.text_input("질의사항 입력", placeholder="여기에 입력해 주세요")
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    
    if user_question == None:
        st.write("아직 질문 내용이 없습니다")
    else:
        pass
        #st.write(user_question)
        
    if user_question:
        st.session_state.conversation = get_conversation_chain(_db, _model, user_question)

if __name__ == "__main__":
    _db = init_db()
    _model = init_model()
    start(_db, _model)
    
