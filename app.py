
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


    
# Create CLI.

#query_text = input("질문: ")
# Prepare the DB.

def get_conversation_chain(db, model, user_question):
    # Search the DB.
    results = db.similarity_search_with_relevance_scores(user_question, k=3)
    if len(results) == 0 or results[0][1] < 0.7:
        print(f"Unable to find matching results.")
        return
    
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
model = ChatOpenAI()
st.set_page_config(page_title="Chat with multiple PDFs",
                       page_icon=":books:")

user_question = st.text_input("질의사항 입력", placeholder="여기에 입력해 주세요")
if user_question:
    st.session_state.conversation = get_conversation_chain(db, model, user_question)
    



    






