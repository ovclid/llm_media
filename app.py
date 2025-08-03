import streamlit as st
from langchain.vectorstores.chroma import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from turfpy.measurement import boolean_point_in_polygon
from geojson import Point, Polygon, Feature
import pandas as pd
import math
import folium
from streamlit_folium import st_folium
import urllib.request
import urllib.parse
import json
import requests
import re
import os

# Constants and configurations
MAIN_CHROMA_PATH = "chroma/main"
MAIN_DATA_PATH = "data/main"
API_KEY_XAI_GROK = os.getenv("API_KEY_XAI_GROK")
API_KEY_KAKAO_MAP = os.getenv("API_KEY_KAKAO_MAP")

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

keywords = ["언급되지 않", "언급이 없", "정보를 알 수 없", "제공할 수 없", "제공되지 않", "알 수 없"]

# Initialize cached resources
@st.cache_resource
def init_db():
    embedding_function = OpenAIEmbeddings()
    db = Chroma(persist_directory=MAIN_CHROMA_PATH, embedding_function=embedding_function)
    return db

@st.cache_resource
def init_model():
    try:
        model = ChatOpenAI(
            model="grok-3-latest",
            api_key=API_KEY_XAI_GROK,
            base_url="https://api.x.ai/v1",
            temperature=0.3,
            max_tokens=1500
        )
    except Exception as e:
        print(f"Failed to initialize ChatOpenAI: {str(e)}. Falling back to default.")
        model = ChatOpenAI()
    return model

@st.cache_resource
def read_press_release_info():
    f = open("./data/온누리상품권_정보.csv", "r", encoding='utf-8')
    data_info = f.readlines()
    for i in range(len(data_info)):
        data_info[i] = data_info[i].split(",")
        data_info[i][1] = data_info[i][1].replace("\n", "")
    return data_info

@st.cache_resource
def get_marketPolygonInfo():
    df = pd.read_csv("market.csv", skipinitialspace=True)
    market_name = df["시장명"].unique()
    market_PolygonInfo = {}
    for i in range(len(market_name)):
        x = list(df[df["시장명"] == market_name[i]].x좌표)
        y = list(df[df["시장명"] == market_name[i]].y좌표)
        temp_pos = [(x[j], y[j]) for j in range(len(x))]
        market_PolygonInfo[market_name[i]] = Polygon([temp_pos])
    return market_PolygonInfo, df

def convert_address_to_pos(address):
    request = "https://dapi.kakao.com/v2/local/search/address.json"
    header = {"Authorization": f"KakaoAK {API_KEY_KAKAO_MAP}"}
    param = {"query": address}
    r = requests.get(request, headers=header, params=param, verify=False)
    info = json.loads(r.text)
    try:
        x = float(info['documents'][0]['x'])
        y = float(info['documents'][0]['y'])
        return (y, x)
    except:
        #msg = "주소를 인식할 수 없어 충북중기청으로 간주합니다."
        #st.markdown(f"<span style='color:red;'>{msg}</span>", unsafe_allow_html=True)
        #st.write(msg)
        #return (36.71466342398,127.43349819)
        return ""
       

def check_newPos(market_PolygonInfo, pos):
    market_name = list(market_PolygonInfo.keys())
    point = Feature(geometry=Point(pos))
    for name in market_name:
        if boolean_point_in_polygon(point, market_PolygonInfo[name]):
            return name
    return ""

def search_url(_data_info, sources):
    urls = []
    temp = list(dict.fromkeys(sources))  # Remove duplicates
    for source in temp:
        title = source.replace(f"{MAIN_DATA_PATH}/", "").replace(".txt", "")
        for data in _data_info:
            if re.sub('[^A-Za-z0-9가-힣]+', '', title) == re.sub('[^A-Za-z0-9가-힣]+', '', data[0]):
                urls.append([title.replace("_", " ").replace("-중소벤처기업부", ""), data[1]])
    return urls

def convert_html(urls):
    html_code = ""
    for url in urls:
        html_code += f'<div><a href="{url[1]}">{url[0]}</a></div>'
    return html_code

def calculate_map_params(pos, target_market, market_PolygonInfo, df_market):
    """
    Calculate the map's center and zoom level based on the address position and target market.
    
    Args:
        pos (tuple): (latitude, longitude) of the input address
        target_market (str): Name of the target market
        market_PolygonInfo (dict): Dictionary of market polygons
        df_market (DataFrame): DataFrame containing market coordinates
    
    Returns:
        tuple: (center_lat, center_lon, zoom_start)
    """
    if pos is None:
        return (36.76423, 127.996334, 12)  # Default values if no valid position
    
    # Get target market coordinates (centroid or representative point)
    market_coords = []
    if target_market in market_PolygonInfo:
        # Calculate centroid of the polygon
        polygon = market_PolygonInfo[target_market]['coordinates'][0]
        lat_sum = sum(coord[0] for coord in polygon) / len(polygon)
        lon_sum = sum(coord[1] for coord in polygon) / len(polygon)
        market_coords = [lat_sum, lon_sum]
    else:
        # Use the market's reference coordinates from df_market
        market_row = df_market[df_market["시장명"] == target_market]
        if not market_row.empty:
            market_coords = [market_row["x좌표"].iloc[0], market_row["y좌표"].iloc[0]]
        else:
            market_coords = [pos[0], pos[1]]  # Fallback to address position
    
    # Calculate bounding box
    lats = [pos[0], market_coords[0]]
    lons = [pos[1], market_coords[1]]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Calculate center
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
    # Calculate distance (in degrees, approximate for zoom estimation)
    lat_diff = max_lat - min_lat
    lon_diff = max_lon - min_lon
    max_diff = max(lat_diff, lon_diff)
    
    # Map distance to zoom level (heuristic)
    if max_diff < 0.005:  # Very close (e.g., within a small area)
        zoom_start = 17
    elif max_diff < 0.01:  # Neighborhood scale
        zoom_start = 15
    elif max_diff < 0.05:  # City scale
        zoom_start = 12
    elif max_diff < 0.1:   # Larger area
        zoom_start = 9
    else:                  # Very far
        zoom_start = 7
    
    return (center_lat, center_lon, zoom_start)

def get_conversation_chain(_db, _model, user_question, _press_release_info, _market_PolygonInfo, _df_market):
    response_text = ""
    urls = []
    results = []
    target_market = ""
    pos = None
    poly_list = None

    question_first = user_question.strip()[0] if user_question.strip() else ""
    
    if question_first == '!':
        response_text = _model.predict("질문은 다음과 같아 : " + 
                                      f"한국산업표준분류코드 6자리 중 {user_question[1:]} 관련 코드를 모두 설명해줘.")
    elif question_first == '@':
        pos = convert_address_to_pos(user_question[1:])
        if pos == "":
            #user_question = "@중심상업2로 48(충북중기청)"
            #pos = (36.71466342398,127.43349819)
            return {"response": "", "error": "주소를 인식할 수 없습니다.", "pos": None}
        
        market_in = check_newPos(_market_PolygonInfo, pos)
        if market_in == "":
            for i in range(len(_df_market)):
                _df_market.loc[i, "거리"] = math.sqrt((_df_market.loc[i, "x좌표"] - pos[0])**2 + (_df_market.loc[i, "y좌표"] - pos[1])**2)
            target_market = _df_market[_df_market["거리"] == _df_market["거리"].min()]["시장명"].to_string(index=False)
        else:
            target_market = market_in
        
        poly_list = list(_market_PolygonInfo[target_market]['coordinates'][0])
        poly_list.pop()
        return {
            "response": "",
            "target_market": target_market,
            "pos": pos,
            "poly_list": poly_list,
            "market_in": market_in
        }
    elif question_first == '#':
        response_text = _model.predict("질문은 다음과 같아 : " + user_question[1:])
    else:
        results = _db.similarity_search_with_relevance_scores(user_question, k=3)
        if len(results) == 0 or results[0][1] < 0.7:
            return {"response": "", "error": "질의하신 내용은 최근 자료와 연관성이 낮습니다."}
        
        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
        prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        prompt = prompt_template.format(common=COMMON_STATEMENT, context=context_text, question=user_question)
        response_text = _model.predict(prompt)
        
        for keyword in keywords:
            if keyword in response_text:
                response_text = _model.predict(COMMON_STATEMENT + 
                                             "질문은 다음과 같아 : " + user_question)
                return {"response": response_text, "urls": [], "results": results}
        
        sources = [doc.metadata.get("source", None).replace("data/sub/", "") for doc, _score in results]
        urls = search_url(_press_release_info, sources)
    
    return {
        "response": response_text,
        "urls": urls,
        "results": results,
        "pos": pos,
        "poly_list": poly_list,
        "target_market": target_market
    }

def start():
    # Initialize resources
    _db = init_db()
    _model = init_model()
    _press_release_info = read_press_release_info()
    _market_PolygonInfo, _df_market = get_marketPolygonInfo()

    st.markdown(f"""<div style="text-align: left; margin-bottom: 13px; ">
        <img src="https://raw.githubusercontent.com/ovclid/llm_media/refs/heads/main/chungbuk_header_logo.svg" width="160"></div>""",
        unsafe_allow_html=True)
        
    # Streamlit UI
    st.markdown("""<div style="font-size: 14px; margin-bottom: 13px;"> ㅇ <a href="https://cbsmba.github.io/onnuri" target="_blank">
            전통시장 및 상점가 구역도(지도기반) </a></div>""", unsafe_allow_html=True)

    user_question = st.text_input(
        "ㅇ 온누리상품권 관련 Q&A(개요, 가맹, 구매 등)",
        placeholder="질의 후 엔터(단, @로 시작하면 주소로 인식)"
    )    
    # Inject JavaScript to scroll up slightly when the input field is focused
    st.components.v1.html(
        """
        <script>
            // Find the Streamlit text input element
            const input = document.querySelector('input[placeholder="질의 후 엔터(단, @로 시작하면 주소로 인식)"]');
            if (input) {
                input.addEventListener('focus', function() {
                    // Scroll up by 100 pixels when the input is focused
                    window.scrollBy({
                        top: 200,
                        behavior: 'smooth'
                    });
                });
            }
        </script>
        """,
        height=0  # Set height to 0 since this is just JavaScript, not visible content
    )


    if "conversation" not in st.session_state:
        st.session_state.conversation = None

    if not user_question:
        return

    # Process the user question
    result = get_conversation_chain(_db, _model, user_question, _press_release_info, _market_PolygonInfo, _df_market)
    
    # Initialize map with default or dynamic parameters
    center_lat, center_lon, zoom_start = (36.76423, 127.996334, 12)  # Default
    if result.get("pos"):
        center_lat, center_lon, zoom_start = calculate_map_params(
            result["pos"], result["target_market"], _market_PolygonInfo, _df_market
        )
    
    _folium_map = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start)

    # Handle the response
    if "error" in result:
        st.markdown(f"<span style='color:red;'>{result['error']}</span>", unsafe_allow_html=True)
        if result['error'] == "주소를 인식할 수 없습니다.":
            st.markdown("확인 후 다시 입력해 주시기 바랍니다. 참고로 충북중기청 주소는 <span style='color:blue;'>'중심상업2로 48' </span>입니다.", unsafe_allow_html=True)
        else:
            st.write("온누리상품권이 아닌 일반적인 내용을 토대로 답변을 원하시면 질문 앞에 #를 붙여주세요.")
        return

    if result["response"]:
        if user_question.strip()[0] == '!':
            st.write(f"!표시에 따라 [{user_question[1:]}]에 대해 KSIC기반으로 답변드리겠습니다.")
            st.write(user_question)
        elif user_question.strip()[0] == '#':
            st.write("#표시에 따라 일반적인 내용을 토대로 답변드리겠습니다.")
        st.write(result["response"])

    if result.get("urls"):
        st.write("----------- 레퍼런스(관련성 높은순) -----------")
        html = convert_html(result["urls"])
        st.markdown(html, unsafe_allow_html=True)
        st.write("\n\n")
        st.write(result["results"])

    if result.get("pos"):
        st.write(f"""입력 주소 좌표 : {result['pos']}""")
        if result["market_in"] == "":
            st.markdown(f"""충북지역 전통시장 및 상점가 중에는 <span style='color:red; font-weight:bold;'>어느 구역에도 속하지 않으며,</span> 가장 가까운 곳은 <span style='color:blue;'>{result['target_market']}</span> 이라 판단됩니다.""", unsafe_allow_html=True)
            #st.markdown(f"""<span style='font-weight:bold;'>다만 가장 가까운 곳은</span> <span style='color:blue;'>{result['target_market']}</span> 이라 판단되며,""", unsafe_allow_html=True)
        else:
            st.markdown(f"충북지역 전통시장 및 상점가 중에는 <span style='color:red;'>{result['market_in']}</span> 안에 위치해 있는 것으로 추정됩니다.", unsafe_allow_html=True)
        st.markdown('[구역도(지도기반)](https://cbsmba.github.io/onnuri)를 클릭하시면 상세하게 확인 가능합니다.')

        # Add red marker for input address
        folium.Marker(
            location=[result["pos"][0], result["pos"][1]],
            popup=user_question[1:],
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(_folium_map)
        
        # Add blue marker for the coordinate with the highest longitude
        if result["poly_list"]:
            # Find the coordinate with the maximum longitude
            rightmost_coord = max(result["poly_list"], key=lambda x: x[1])
            folium.Marker(
                location=rightmost_coord,  # Coordinate with highest longitude
                popup=result["target_market"],
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(_folium_map)
        
        # Add polygon
        folium.Polygon(
            locations=result["poly_list"],
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.4,
            popup=result["target_market"]
        ).add_to(_folium_map)
        
        # Render map with fixed height for mobile compatibility
        st_folium(_folium_map, width="100%", height=200)

if __name__ == "__main__":
    start()
