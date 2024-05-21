from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.chroma import Chroma
import os
import shutil
#from dotenv import load_dotenv
import datetime
import glob

MAIN_CHROMA_PATH = "chroma/main"
SUB_CHROMA_PATH = "chroma/sub"

MAIN_DATA_PATH = "data/main"
SUB_DATA_PATH = "data/sub"

BACKUP_CHROMA_PATH = "chroma/backup"
BACKUP_MAIN_CHROMA_PATH = "chroma/backup/main"
BACKUP_SUB_CHROMA_PATH = "chroma/backup/sub"

date_info = datetime.datetime.today().strftime('%Y%m%d_%H%M')[2:]

dirs = [MAIN_CHROMA_PATH, SUB_CHROMA_PATH,
          MAIN_DATA_PATH, SUB_DATA_PATH,
          BACKUP_CHROMA_PATH, BACKUP_MAIN_CHROMA_PATH, BACKUP_SUB_CHROMA_PATH]

def check_dirs(dirs):
    for directory in dirs:
        if os.path.exists(directory) != True:
            print(f"{directory}가 존재하지 않아 새로 생성!!")
            os.mkdir(directory)
                
def load_documents(directory_path, file_type):
    loader = DirectoryLoader(directory_path, glob=f"**/*.{file_type}")
    documents = loader.load()
    return documents

def split_text(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")

    document = chunks[4]
    print(document.page_content)
    print(document.metadata)

    return chunks

def backup_directory(src_dir, des_dir) :
    global date_info
   
    if os.path.exists(src_dir):
        shutil.copytree(src_dir, des_dir + "/"+ date_info)

def load_chromadb(chromadb_path):
    db = Chroma(persist_directory=chromadb_path,
                        embedding_function = OpenAIEmbeddings())

    return db

# 디렉토리 확인하기
input("디렉토리 확인하기")
check_dirs(dirs)

# 새로운 DB 생성하기
input("새로운 DB 생성하기")
documents = load_documents(SUB_DATA_PATH, "txt")
chunks = split_text(documents)
backup_directory(SUB_CHROMA_PATH, BACKUP_SUB_CHROMA_PATH)
new_db = Chroma.from_documents(chunks,
                               OpenAIEmbeddings(),
                               persist_directory=SUB_CHROMA_PATH)
new_db.persist()

# 기존 메인DB 백업
input("기존 메인DB 백업 및 읽어오기")
backup_directory(MAIN_CHROMA_PATH, BACKUP_MAIN_CHROMA_PATH)
main_db = load_main_chromadb(MAIN_CHROMA_PATH)

# 기존 메인DB와 새로 생성한 DB 합치기
input("기존 메인DB와 새로 생성한 DB 합치기")
if main_db != ' ':    #기존 메인 디비가 없을 경우
    shutil.copytree(SUB_CHROMA_PATH, MAIN_CHROMA_PATH)
else:
    new_db_info = new_db._collection.get(include=['documents','metadatas','embeddings'])
    main_db._collection.add(
        embeddings=new_db_info['embeddings'],
        metadatas=new_db_info['metadatas'],
        documents=new_db_info['documents'],
        ids=new_db_info['ids']
    )

# 합쳐진 DB 저장하기
input("합쳐진 DB 저장하기")
main_db.persist()

"""
# SUB_DATA_PATH 파일들을 MAIN_DATA_PATH로 복사
input("SUB_DATA_PATH 파일들을 MAIN_DATA_PATH로 복사")
shutil.copy(SUB_DATA_PATH, MAIN_DATA_PATH)
"""

# SUB_DATA_PATH 모든 파일 지우기
input("SUB_DATA_PATH 모든 파일 지우기")
filelist = glob.glob(os.path.join(SUB_DATA_PATH, "*.*"))
for f in filelist:
    os.remove(f)
    
# SUB_CRHOMA_PATH 모두 지우기
#shutil.rmtree(SUB_CHROMA_PATH)
