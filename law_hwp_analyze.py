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

MAIN_CHROMA_PATH = "chromadb\\chroma\\main"
MAIN_DATA_PATH = "chromadb\\data\\main"
SUB_CHROMA_PATH  = "chromadb\\chroma\\sub"
SUB_DATA_PATH = "chromadb\\data\\sub"

COMMON_STATEMENT = """질문자는 대한민국 공무원들힙니다.
대답은 진철하게 설명하는 방식으로 부탁합니다."""

PROMPT_TEMPLATE = """
        {common}
        
        답변은 아래의 내용만을 근거로 해서 해야합니다. :

        {context}

        ---

        위 내용에 근거해서 답변을 해주시기 바랍니다. : {question}
"""

keywords = ["언급되지 않", "언급이 없", "정보를 알 수 없", "제공할 수 없", "제공되지 않" , "알 수 없"]

def search_url (_data_info, sources):
    urls = []
    #sources 중복 제거
    temp = []
    for source in sources:
        if source not in temp:
            temp.append(source)
    sources = temp
    
    for source in sources:
        #st.write(f"{MAIN_DATA_PATH}\\")
        #st.write(f"{SUB_DATA_PATH}\\")
        #st.write(source)
        
        #title = source.replace(f"{MAIN_DATA_PATH}\\", "").replace(f"{SUB_DATA_PATH}\\", "").replace(".txt", "")    ### 코드 수정 필요!!!! linux와 호환성 문제 발생
        title = os.path.splitext(os.path.basename(source))[0]
        print(title)
        for data in _data_info:
            if title == data[0]:
                print(data)
                urls.append([title.replace("_", " ").replace("-중소벤처기업부", ""), data[1]])
    return urls

def convert_html(urls):
    html_code = ""
                            
    for i in range(len(urls)):
        html_code += f'''<div><a href="{urls[i][1]}">{urls[i][0]}</a></div>'''
    print(html_code)
    return html_code

# Prepare the DB.
@st.cache_data
def get_conversation_chain(_db, _model, user_question, _press_release_info):
    # Search the DB.
    #st.write(user_question)

    qestion_first = user_question.strip()[0]
    if qestion_first == '@':
        st.write("@표시에 따라 고등학생 입장에서 답변드리겠습니다.")
        response_text = _model.predict("대한민국 고등학생에게 선생님이 답변하는 방식으로 해줘." + \
                                       "질문은 다음과 같아 : " + \
                                       user_question)
        st.write(response_text)
    elif qestion_first == '#':
        st.write("#표시에 따라 제가 보유한 정보만을 토대로 답변드리겠습니다.")
        response_text = _model.predict(COMMON_STATEMENT + \
                                       "질문은 다음과 같아 : " + \
                                       user_question)
        st.write(response_text)
    else :
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
                st.write("관련자료를 찾을 수 없습니다. 다만 제 정보를 토대로 답변드리면...")
                response_text = _model.predict(COMMON_STATEMENT + \
                                       "질문은 다음과 같아 : " + \
                                       user_question)
                st.write(response_text)

                return response_text
                    
        sources = [doc.metadata.get("source", None) for doc, _score in results]
        formatted_response = f"Response: {response_text}\nSources: {sources}"
        print(formatted_response)
    
        st.write(response_text)
        st.write("----------- 레퍼런스(관련성 높은순) -----------")
        urls = search_url (_press_release_info, sources)
        html = convert_html(urls)
        st.markdown(html,unsafe_allow_html=True)
        st.write("\n\n")
        st.write(results)
      
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

@st.cache_resource
def read_press_release_info():
    #f = open("./data/보도자료_정보.csv", "r", encoding='ISO-8859-1')

    files =[ "./chromadb/data/latest_법령정보.csv"]

    total_info = []

    for file_name in files:
        f = open(file_name, "r", encoding='utf-8')
        data_info = f.readlines()

        for i in range(len(data_info)):
            data_info[i] = data_info[i].split(",")
            data_info[i][1] = data_info[i][1].replace("\n", "")
            total_info.append(data_info[i])
            
        f.close()

    return total_info


def start(_db, _model, _press_release_info):
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
        st.session_state.conversation = get_conversation_chain(_db, _model, user_question, _press_release_info)

if __name__ == "__main__":
    _db = init_db()
    _model = init_model()
    _press_release_info = read_press_release_info()
    
    start(_db, _model, _press_release_info)
