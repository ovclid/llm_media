import streamlit as st
#from dotenv import load_dotenv
#import argparse
#from dataclasses import dataclass
from langchain.vectorstores.chroma import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

#from langchain_xai import ChatXAI

from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os
import shutil
import re

from turfpy.measurement import boolean_point_in_polygon
from geojson import Point, Polygon, Feature
import pandas as pd
import math

import folium
from streamlit_folium import st_folium

import urllib.request
import urllib.parse
import json
import bs4
import requests

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

MAIN_CHROMA_PATH = "chroma/main"
MAIN_DATA_PATH = "data/main"

XAI_API_KEY = os.getenv("XAI_API_KEY")
KAKAO_MAP_API_KEY = os.getenv("KAKAO_MAP_API_KEY")

COMMON_STATEMENT = """참고로 본부는 중소벤처기업부를 의미하고 중기부는 중소벤처기업부를 의미합니다.
기재부는 기획재정부의 약칭이며, 산업부는 산업통상자원부의 약칭입니다.   
지방청은 지방중소벤처기업청을 의미합니다.
지방청은 지방정부 소속기관이 아닙니다.

충북청, 충북중기청, 충북지방중소벤처기업청은 모두 같은 단어입니다.  
충북청은 중앙부처인 중소벤처기업부의 소속기관입니다.
충북청은 충청북도 소속의 지방정부 기관이 아닙니다.
"""

PROMPT_TEMPLATE = """
        {common}
        
        답변은 아래의 내용만을 근거로 해서 해야합니다. :

        {context}

        ---

        위 내용에 근거해서 자세하고 친절하게 답변을 해주시기 바랍니다. : {question}
"""

keywords = ["언급되지 않", "언급이 없", "정보를 알 수 없", "제공할 수 없", "제공되지 않" , "알 수 없"]

def add_map(address, pos, polygon_coords):
    # Folium 지도 생성
    m = folium.Map(location=[pos[0], pos[1]], zoom_start=12)  
    
    # 빨간색 마커 추가
    marker_location = [pos[0], pos[1]]  
    folium.Marker(
        location=marker_location,
        popup="입력 주소",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

    st.write(polygon_coords)
    folium.Polygon(
        locations=[polygon_coords],
        color="blue",
        fill=True,
        fill_color="blue",
        fill_opacity=0.4,
        popup="샘플 다각형"
    ).add_to(m)
    
    # Streamlit에 지도 렌더링
    st_folium(m, width=700, height=500)
        
def convert_address_to_pos(address):
    #encoding_address = urllib.parse.quote_plus(address)
    request = f"https://dapi.kakao.com/v2/local/search/address.json"

    key = f"Authorization: KakaoAK {KAKAO_MAP_API_KEY}"
    header = {"Authorization":f"KakaoAK {KAKAO_MAP_API_KEY}"}
    param = {"query": f"{address}"}
    r=requests.get(request, headers=header, params = param, verify=False)

    info = json.loads(r.text)
    try:
      x = float(info['documents'][0]['x'])
      y = float(info['documents'][0]['y'])
    except:
      return ""
      
    return (y, x)

def check_newPos(market_PolygonInfo, pos):
    market_name = list(market_PolygonInfo.keys())
    point = Feature(geometry=Point(pos))
    
    for i in range(len(market_name)):
        #print(market_name[i], "에 해당하는지 검사중...")
        if (boolean_point_in_polygon(point, market_PolygonInfo[market_name[i]])):
            #print(market_name[i],  pos)
            return market_name[i]

    return ""
  
def search_url (_data_info, sources):
    urls = []
    #sources 중복 제거
    temp = []
    for source in sources:
        if source not in temp:
            temp.append(source)
    sources = temp
    #st.write(sources)
  
    for source in sources:
        title = source.replace(f"{MAIN_DATA_PATH}/", "").replace(".txt", "")
        print(title)
        #st.write(title)

        for data in _data_info:
            #if title == data[0]:
            if re.sub('[^A-Za-z0-9가-힣]+', '', title) == re.sub('[^A-Za-z0-9가-힣]+', '', data[0]):
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
def get_conversation_chain(_db, _model, user_question, _press_release_info, _market_PolygonInfo, _df_market):
    # Search the DB.
    #st.write(user_question)

    qestion_first = user_question.strip()[0]
    if qestion_first == '!':
        st.write(f"!표시에 따라 [{user_question[1:]}]에 대해 KSIC기반으로 답변드리겠습니다.")
        user_question = f"한국산업표준분류코드 6자리 중 {user_question[1:]} 관련 코드를 모두 설명해줘."
        st.write(user_question)
        response_text = _model.predict("질문은 다음과 같아 : " + \
                                       user_question)
        st.write(response_text)    
    elif qestion_first == '@':
        st.write("@표시에 따라 주소로 인식하여 처리합니다.")
        pos = convert_address_to_pos(user_question[1:])
        st.write(f"""'{user_question[1:]}' 좌표 변환 : {pos}""")            
        if pos == "":
          st.markdown(f"""<span style='color:red;'>주소를 인식할 수 없습니다.</span> 주소 확인 후 다시 입력해 주시기 바랍니다.""", unsafe_allow_html=True)
                
        else:
          market_in = check_newPos(_market_PolygonInfo, pos)
          if market_in == "":
            for i in range(len(_df_market)):
                _df_market.loc[i, "거리"] = math.sqrt( (_df_market.loc[i, "x좌표"] - pos[0])**2 + (_df_market.loc[i, "y좌표"] - pos[1])**2 )
            
            market_nearest = _df_market[_df_market["거리"] == _df_market["거리"].min()]["시장명"].to_string(index=False)
            st.markdown(f"""<span style='color:red; font-weight:bold;'>어느 구역에도 속하지 않습니다.</span>""", unsafe_allow_html=True)
            st.markdown(f"""<span style='font-weight:bold;'> 다만 가장 가까운 곳은</span> <span style='color:blue;'>{market_nearest}</span> 이라 판단됩니다.""", unsafe_allow_html=True)
            st.markdown('[구역도(지도기반)](https://cbsmba.github.io/onnuri)를 클릭하여 재확인 하시는 것을 추천드립니다.')
            #st.write(_market_PolygonInfo[market_nearest])
            polygon_coords = _market_PolygonInfo[market_nearest]
          else:
            st.markdown(f"<span style='color:red;'>{market_in}</span> 안에 위치해 있습니다.", unsafe_allow_html=True)
            st.markdown('[구역도(지도기반)](https://cbsmba.github.io/onnuri)를 클릭하여 재확인 하는 것을 추천드립니다.')
            #st.write(_market_PolygonInfo[market_in])
            polygon_coords = _market_PolygonInfo[market_in]
        
        add_map(user_question[1:], pos, polygon_coords)
        response_text = ""  #없으면 에러    
    elif qestion_first == '#':
        st.write("#표시에 따라 일반적인 내용을 토대로 답변드리겠습니다.")
        response_text = _model.predict("질문은 다음과 같아 : " + \
                                       user_question[1:])
        st.write(response_text)
    else :
        results = _db.similarity_search_with_relevance_scores(user_question, k=3)
    
        if len(results) == 0:
            st.write("질의하신 내용은 최근 자료와 연관성이 매우 낮습니다.")
            st.write("온누리상품권의의 일반적인 내용을 토대로 답변을 원하시면 질문 앞에 #를 붙여주세요.")
            return
            
        if results[0][1] < 0.7:
            print(f"Unable to find matching results.")
            st.write("질의하신 내용은 최근 자료와 연관성이 낮습니다.")
            st.write("온누리상품권이 아닌 일반적인 내용을 토대로 답변을 원하시면 질문 앞에 #를 붙여주세요.")
            return
        
        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
        prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        prompt = prompt_template.format(common = COMMON_STATEMENT, context=context_text, question=user_question)
        print(prompt)
    
        response_text = _model.predict(prompt)
        for keyword in keywords:
            if keyword in response_text:
                st.write("관련 자료를 찾을 수 없습니다. 다만 온누리상품권이 아닌 일반적인 내용을 토대로 답변드리면...")
                response_text = _model.predict(COMMON_STATEMENT + \
                                       "질문은 다음과 같아 : " + \
                                       user_question)
                st.write(response_text)

                return response_text
                    
        sources = [doc.metadata.get("source", None) for doc, _score in results]
        for i in range(len(sources)):
          sources[i] = sources[i].replace("data/sub/", "")  #chromadb merge시에 포함된 디렉토리 정보 삭제 필요
          
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
    try:
      model = ChatOpenAI(
          model= "grok-3-latest", #"grok-4-0709",  # Grok 3 모델 지정
          api_key=XAI_API_KEY,
          base_url="https://api.x.ai/v1",
          temperature=0.3,
          max_tokens=1000
      )
  
     #   model = ChatXAI(
     #       model="grok-4",
     #       #model="grok-3",
     #       temperature=0,
     #       max_tokens=None,
     #       timeout=None,
     #       max_retries=2,
     #   )
    except Exception as e:
        st.write(f"Failed to initialize ChatXAI: {str(e)}. Falling back to ChatOpenAI.")
        model = ChatOpenAI()
    return model

@st.cache_resource
def read_press_release_info():
    #f = open("./data/보도자료_정보.csv", "r", encoding='ISO-8859-1')
    f = open("./data/온누리상품권_정보.csv", "r", encoding='utf-8')
    data_info = f.readlines()

    for i in range(len(data_info)):
        data_info[i] = data_info[i].split(",")
        data_info[i][1] = data_info[i][1].replace("\n", "")
    return data_info

@st.cache_resource
def get_marketPolygonInfo():
  ## 시장좌표 파일을 바탕으로 시장별 구역도를 다각형 정보로 변환          
  df = pd.read_csv("market.csv", skipinitialspace=True)
  market_name = df["시장명"].unique()

  market_PolygonInfo = {}
  for i in range(len(market_name)):
      x = list(df[ df["시장명"] ==  market_name[i]].x좌표)
      y = list(df[ df["시장명"] ==  market_name[i]].y좌표)

      temp_pos = []
      for j in range(len(x)):
          temp_pos.append( (x[j], y[j]))    

      #market_PosInfo[market_name[i]] = temp_pos
      market_PolygonInfo[market_name[i]] = Polygon([temp_pos])

  #st.write(market_name)
  #st.write(market_PolygonInfo)

  return market_PolygonInfo, df
  
def start(_db, _model, _press_release_info, _market_PolygonInfo, _df_market):
    #st.set_page_config(page_title="Chat with multiple PDFs", page_icon=":books:")
    st.markdown('[충북 전통시장 및 상점가 구역도(지도기반)](https://cbsmba.github.io/onnuri)')

    # 공백 추가
    st.markdown("<br>", unsafe_allow_html=True)
    user_question = st.text_input("온누리상품권 관련 Q&A", placeholder="여기에 질의 입력 후 엔터(단, 질의 앞에 @를 붙이면 주소로 인식)")
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    
    if user_question == None:
        st.write("아직 질문 내용이 없습니다")
    else:
        pass
        #st.write(user_question)
    #st.write("질의사항 앞에 @를 붙이면 주소로 인식하여 구역내 포함 여부를 확인할 수 있습니다.")
    if user_question:
        st.session_state.conversation = get_conversation_chain(_db, _model, user_question, _press_release_info, _market_PolygonInfo, _df_market)

if __name__ == "__main__":
    _db = init_db()
    _model = init_model()
    _press_release_info = read_press_release_info()
    _market_PolygonInfo, _df_market = get_marketPolygonInfo()
    start(_db, _model, _press_release_info, _market_PolygonInfo, _df_market)
