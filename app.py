
import streamlit as st
#from dotenv import load_dotenv
#import argparse
#from dataclasses import dataclass
from langchain.vectorstores.chroma import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

CHROMA_PATH = "chroma/main"

PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

import streamlit as st
import pandas as pd

st.write("Here's our first attempt at using data to create a table:")
st.write(pd.DataFrame({
    'first column': [1, 2, 3, 4],
    'second column': [10, 20, 30, 40]
}))


    
# Create CLI.

#query_text = input("질문: ")
# Prepare the DB.

def get_conversation_chain(db, model, user_question):
    # Search the DB.
    st.write(user_question)
    results = db.similarity_search_with_relevance_scores(user_question, k=3)

    if len(results) == 0:
        st.write(f"검색 결과 : {len(results)}.")
        return
        
    if results[0][1] < 0.7:
        print(f"Unable to find matching results.")
        st.write("검색 결과 유사성이 거의 없습니다.")
        return
    
    st.write(results)
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=user_question)
    print(prompt)

    response_text = model.predict(prompt)
    sources = [doc.metadata.get("source", None) for doc, _score in results]
    formatted_response = f"Response: {response_text}\nSources: {sources}"
    print(formatted_response)

    st.write(formatted_response)
    return response_text

#load_dotenv()
embedding_function = OpenAIEmbeddings()
db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
#st.write(temp.items()[0])
temp = db.get()
st.write(len(temp))
#st.write(temp[0][:20])

model = ChatOpenAI()
#st.set_page_config(page_title="Chat with multiple PDFs", page_icon=":books:")

user_question = st.text_input("질의사항 입력", placeholder="여기에 입력해 주세요")
if "conversation" not in st.session_state:
    st.session_state.conversation = None
        
if user_question:
    st.session_state.conversation = get_conversation_chain(db, model, user_question)
    



    






