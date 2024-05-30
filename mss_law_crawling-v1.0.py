from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time, datetime, os, subprocess
import openpyxl
import re, shutil, glob
import pathlib

def error_report(driver, download_path, title):
    f = open(f"{download_path}/!!!_다운로드 에러_!!!.txt", "a")
    f.write(driver.current_url + "\n")
    f.write(title + "\n\n")
    f.close()
   
def start_webdriver(url):    
    serv = Service("C:/chromedriver/chromedriver.exe")
    serv.creation_flags = subprocess.CREATE_NO_WINDOW   
    driver = webdriver.Chrome(service = serv)
    driver.maximize_window()

    driver.get(url)
    time.sleep(3)

    return driver

def make_download_folder():
    now = datetime.datetime.now()

    download_path = os.getcwd().replace("\\", "/") + "/download/"
    if os.path.exists(download_path) == False:
        os.mkdir(download_path)
        
    folder_name = str(now).replace("-", "")[:14].replace(":", "").replace(" ", "_")
    download_path = download_path + folder_name
    if os.path.exists(download_path) == False:
        os.mkdir(download_path)
    
    return download_path

def save_laws_info(all_laws_info, download_path, download_info_file_name):
    f = open(download_path + "/" + download_info_file_name, "w", encoding = 'utf-8') 
    for info in all_laws_info:
        f.write(",".join(info))
        f.write("\n")

    f.close()

def delete_dir_all_files(folder):
    if os.path.exists(folder) == False:
        return False
    
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    return True

def save_copy_file_info(latest_copy_path, copy_targets, download_info_file_name):
    f = open(download_path + '/' +download_info_file_name, "r", encoding ="utf-8")
    all_saved_file_info = f.readlines()
    f.close()
    
    all_selected_file_info = []
    for saved_file_info in all_saved_file_info:
        file_name = saved_file_info.split(",")[0]
        for copy_target in copy_targets:
            if file_name in copy_target:
                all_selected_file_info.append(saved_file_info)

    f = open(latest_copy_path + '/' +download_info_file_name, "w", encoding ="utf-8")
    for slected_file_info in all_selected_file_info:
        f.write(slected_file_info)

    f.close()
    
             
def copy_files(download_path, latest_copy_path, key_words):
    files = glob.glob(f"{download_path}/*.hwp*")
    copy_targets = []

    for file in files:
        for key_word in key_words:
            if key_word in file:
                copy_targets.append(file)
                print(key_word, file)
                continue
   
    if len(copy_targets) != 0:
        #make_dir(latest_copy_path)
        check_delete = delete_dir_all_files(latest_copy_path)
        if check_delete == False:    # 폴더가 없으면 새로 생성하
            os.mkdir(latest_copy_path)
            
        for copy_target in copy_targets:
            head, tail = os.path.split(copy_target)
            shutil.copyfile(copy_target, f'{latest_copy_path}/'+tail)

    return copy_targets

def download_wait(directory, timeout, nfiles=None):
    seconds = 0

    dl_wait = True
    while dl_wait and seconds<timeout:
        time.sleep(1)
        dl_wait = False
        files = os.listdir(directory)
        if nfiles and len(files) != nfiles:
            dl_wait = True

        for fname in files:
            if fname.endswith('.crdownload'):
                dl_wait = True

        seconds += 1

    return seconds

def get_recent_file(folder_path):
    # 폴더 내 모든 파일 가져오기
    files = os.listdir(folder_path)

    # 파일들의 생성 시간을 기준으로 정렬
    sorted_files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(folder_path, x)))

    # 가장 최근 파일명 리턴
    return sorted_files[-1]

def start_crwaling(download_path, limit_num = -1):
    url_dict = {
    "중소벤처기업부" : "https://www.law.go.kr/LSW/lsAstSc.do?\
menuId=391&subMenuId=397&tabMenuId=437&cptOfiCd=1421000&\
eventGubun=060102#cptOfi1421000",
}  
    #default_download = "C:/Users/smba/Downloads"
    default_download = str(pathlib.Path.home() / "Downloads")
    department = "중소벤처기업부"

    driver = start_webdriver(url_dict[department])

    #예정법령정보 체크 해제 및 선택
    print("예정법령정보 체크 해제 및 선택")
    WebDriverWait(driver, 60).until(EC.visibility_of_element_located(("id", "efCheck"))).click()
    WebDriverWait(driver, 60).until(EC.visibility_of_element_located(("xpath", '//*[@id="pageFrm"]/div[1]/a'))).click()

    time.sleep(3)

    all_laws_info = []

    for next_page_num in range(2):
        table_tr_eles = driver.find_elements("xpath", '//*[@id="resultTable"]/tbody/tr')

        ###################################################
        if limit_num != -1:
            print(f"임시 테스트용으로 {limit_num}개 법령만 저장...!!!") # 임시 테스트용
            table_tr_eles = table_tr_eles[:limit_num] # 임시 테스트용 (주석 처리 필요)
        ###################################################
        
        for i in range(len(table_tr_eles)):
            
            tds_ele = table_tr_eles[i].find_elements("tag name", "td")
            for ele in tds_ele:
                print(ele.text)

            
            tds_ele[1].find_element("tag name", "a").click()
            time.sleep(2)
            driver.switch_to.window(driver.window_handles[1])
            time.sleep(1)
            url = driver.current_url
            
            save_popup_ele = driver.find_element("id", "bdySaveBtn")
            save_popup_ele.click()
            time.sleep(2)
            
            save_eles = driver.find_elements("id", "aBtnOutPutSave")
            save_eles[1].click()
            time.sleep(3)
            driver.close()

            try:
                download_wait(default_download, 300, nfiles=None)
            except:
                print("!!!!!!! 파일 다운로드 실패!!!!!!!")
                error_report(driver, download_path, tds_ele[1].text)
                driver.back()

            try:
                file_name = get_recent_file(default_download)
                shutil.move(default_download+'/'+file_name, download_path + '/' + file_name)
            except:
                print("!!! 다운로드 파일 이동-move 실패 !!!")
                error_report(driver, download_path, tds_ele[1].text)
                driver.back()
                continue
            law_info = [file_name.split(".hwp")[0], url]
            
            all_laws_info.append(law_info)
            driver.switch_to.window(driver.window_handles[0])
            table_tr_eles = driver.find_elements("xpath", '//*[@id="resultTable"]/tbody/tr')
            print(law_info)
            print()
            
        xpath = '//*[@id="pageFrm"]/div[3]/div/ol[2]/li/a'
        driver.find_element("xpath", xpath).click()
        time.sleep(3)

    return all_laws_info

################### 1단계(크롤링) ####################
print("1-1단계 : 중기부 관련 법령정보 크롤링(다운로드)")
download_path = make_download_folder()
all_laws_info = start_crwaling(download_path,
                               -1)   # 테스트를 위해 다운로드 페이지당 개수 제한 가능 (-1 경우 모두)

print("1-2단계 : 모든 다운로드 법령파일에 대한 정보 저장(url)")
download_info_file_name = "latest_법령정보.csv"
save_laws_info(all_laws_info, download_path, download_info_file_name)

################### 2단계(선택적 저장) ################
print("2-1단계 : key_words에 포함된 단어만 선택적으로 최신 폴더로 저장")
key_words = ["(법률)", "상생조정", "수출지원센터", "국공립", "비영리법인", "소속기관 직제"]
latest_copy_path = "./download/latest_copy"
copy_targets = copy_files(download_path, latest_copy_path, key_words)

print("2-2단계 : 선택적으로 저장한 파일 정보를 최신 폴더에 저장")
save_copy_file_info(latest_copy_path, copy_targets, download_info_file_name)
