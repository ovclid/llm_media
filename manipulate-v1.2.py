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
import sys

MAIN_CHROMA_PATH = "chroma/main"
SUB_CHROMA_PATH = "chroma/sub"

MAIN_DATA_PATH = "data/main"
SUB_DATA_PATH = "data/sub"

BACKUP_CHROMA_PATH = "chroma/backup"
BACKUP_MAIN_CHROMA_PATH = "chroma/backup/main"
BACKUP_SUB_CHROMA_PATH = "chroma/backup/sub"

BACKUP_DATA_PATH = "data/backup"
BACKUP_MAIN_DATA_PATH = "data/backup/main"
BACKUP_SUB_DATA_PATH = "data/backup/sub"

date_info = datetime.datetime.today().strftime('%Y%m%d_%H%M')[2:]

dirs = [MAIN_CHROMA_PATH, SUB_CHROMA_PATH,
          MAIN_DATA_PATH, SUB_DATA_PATH,
          BACKUP_CHROMA_PATH, BACKUP_MAIN_CHROMA_PATH, BACKUP_SUB_CHROMA_PATH,
          BACKUP_DATA_PATH, BACKUP_MAIN_DATA_PATH, BACKUP_SUB_DATA_PATH]

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

def copy_files(src_dir, des_dir):
    filelist = glob.glob(os.path.join(src_dir, "*.*"))

    for f in filelist:
        shutil.copy(f, des_dir)
    
def load_chromadb(chromadb_path):
    filelist = glob.glob(os.path.join(chromadb_path, "*.*"))
    if filelist == []:
        print(f"{chromadb_path} 폴더에 아무 내용이 없습니다.")
        return False
    
    db = Chroma(persist_directory=chromadb_path,
                        embedding_function = OpenAIEmbeddings())

    return db

############## 사전 점검 및 신규 DB 생성  ######################
## [사전 점검] 필요한 디렉토리들 생성
## [신규DB 생성 및 저장] 
##########################################################

# [사전 점검] 디렉토리 확인하기
input("디렉토리 확인하기")
check_dirs(dirs)

# [신규 DB] 생성 및 저장하기
input("새로운 DB 생성하기")
documents = load_documents(SUB_DATA_PATH, "txt")
chunks = split_text(documents)
new_db = Chroma.from_documents(chunks,
                               OpenAIEmbeddings(),
                               persist_directory=SUB_CHROMA_PATH)
new_db.persist()

############## 기존 DB 백업 및 신규와 합치기  ###################
## [DB 백업] 기존의 Main 크로마 디비와 데이터 각각  백업
## [DB 합치기] 기존의 Main 과 신규 Sub 디비 합치기
##########################################################

# 기존 메인DB 백업
input("기존 메인DB 백업 및 읽어오기")
backup_directory(MAIN_CHROMA_PATH, BACKUP_MAIN_CHROMA_PATH)
backup_directory(MAIN_DATA_PATH, BACKUP_MAIN_DATA_PATH)

main_db = load_chromadb(MAIN_CHROMA_PATH)

# 기존 메인DB와 새로 생성한 DB 합치기
input("기존 메인DB와 새로 생성한 DB 합치기")

if main_db == False:
    print(f"{MAIN_CHROMA_PATH}에 아무 내용이 없어 sub db를 main으로 복사")
    shutil.copytree(SUB_CHROMA_PATH, MAIN_CHROMA_PATH, dirs_exist_ok = True)
elif  main_db._collection.get(include=['uris'])["ids"] == [] :    #기존 메인 디비가 없을 경우
    #shutil.copytree(SUB_CHROMA_PATH, MAIN_CHROMA_PATH)
    print("main db가 없거나 로딩을 실패하여 프로그램을 종료합니다")
    sys.exit()    
else:
    new_db_info = new_db._collection.get(include=['documents','metadatas','embeddings'])
    main_db._collection.add(
        embeddings=new_db_info['embeddings'],
        metadatas=new_db_info['metadatas'],
        documents=new_db_info['documents'],
        ids=new_db_info['ids']
    )

######### DB Merge 이후 후속 조치 작업 ###########################
## [sub data] (1) 백업 폴더에 저장, (2) main data로 추가 복사, (3) sub data 삭제
## [sub db]   (1) 백업 폴더에 저장
#############################################################

# sub data 처리하기
input(f"{SUB_DATA_PATH} 백업, {MAIN_DATA_PATH} 추가 복사, {SUB_DATA_PATH} 파일 삭제")
backup_directory(SUB_DATA_PATH, BACKUP_SUB_DATA_PATH)   # 트리구조 전체 백업
copy_files(SUB_DATA_PATH, MAIN_DATA_PATH) # 서브 데이터를 메인 데이터로 복사하기
filelist = glob.glob(os.path.join(SUB_DATA_PATH, "*.*"))
for f in filelist:
    os.remove(f)

# sub chromadb 처리하기
input(f"{SUB_CHROMA_PATH} 백업 / 자료는 삭제 하지 않고 그대로 둠")
backup_directory(SUB_CHROMA_PATH, BACKUP_SUB_CHROMA_PATH) # 트리구조 전체 백업
