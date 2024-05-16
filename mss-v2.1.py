from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

import requests
import openpyxl
import pandas as pd
import time, datetime, os, subprocess, re, shutil,pathlib

import ss_source_file_update as ssup
import ss_auto_chromedriver as ssdriver

###################### 주요 변수 정의하기 ###################
DATECHECK_DEADLINE_DAYS = 30      # 현재부터 정해진 날짜 전까지의 보도자료 수집
ONLY_NEW_FILES_DOWNLOAD = True

only_new = input("최신 자료만 자동으로 다운로드할까요?(y/n) ")
if only_new.upper() == "Y":
    ONLY_NEW_FILES_DOWNLOAD = True
else:
    ONLY_NEW_FILES_DOWNLOAD = False

    DATECHECK_DEADLINE_DAYS = int(input("언제 전까지의 자표를 다운로드할까요?(일수 입력) "))

    
total_cnt = 0
stop_program = False
articles_per_page = 10
news_release_all_info = []
file_ext = ('.hwp', '.hwpx',  '.pdf', '.xlsx', '.ppt', '.pptx', '.doc', 'docx', '.png', '.jpg', '.jpeg')
default_download = str(pathlib.Path.home() / "Downloads")   # "C:/Users/smba/Downloads"

url_dict = {
    "중소벤처기업부" : "https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=86",
}
ministry = "중소벤처기업부"

download_info_url = "https://raw.githubusercontent.com/ovclid/llm_media/main/data/보도자료_정보.csv"
download = requests.get(download_info_url)
download_files_info = download.text

############# 다운로드 에러 발생시 로그(url, 제목) 저장  #################
def error_report(driver, download_path, title):
    f = open(f"{download_path}/!!!_다운로드 에러_!!!.txt", "a", encoding = "utf-8")
    f.write(driver.current_url + "\n")
    f.write(title + "\n\n")
    f.close()

########### 기존에 보도자료 첨부파일 다운로드를 했는지 체크  ###########
def check_prev_download(download_files_info, current_url):
    if current_url in download_files_info[:300] :
        print("기존에 이미 받은 자료입니다")
        print(current_url)
        return False
    else:
        return True
    
############# 보도자료 정보(제목, url) 저장  #################
def save_news_release_info(driver, download_path, news_release_info):
    file_name = ""
    url_link = ""

    for info in news_release_info:
        if info.lower().endswith(('.hwp', '.hwpx', '.pdf')) :
            file_name = info.split(".")[0]
        if info.lower().startswith(('http')) :
            url_link = info

    if file_name != "":
        f = open(f"{download_path}/보도자료.csv", "a", encoding="utf-8")
        f.write(file_name + "," + url_link + "\n")
        f.close()
    else:
        print(current_news_release_info, "관련정보 저장 실패")

################ 웹드라이버 구동 #####################
def start_webdriver(url):    
    driver = ssdriver.start()
    driver.maximize_window()
    driver.get(url)
    
    time.sleep(3)
    
    return driver

############### 첨부파일 저장 폴더 생성 ##################
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

############### 첨부파일 게시일자 가져오기 ##################
def get_date_from_filename(file_name):    ## 테스트가 더 필요
    date_pattern_6digit = re.compile("\d{6}")
    date_pattern_4digit = re.compile("\d{4}")

    dates = date_pattern_6digit.findall(file_name[:20])
    if dates != []:
        return "20"+dates[0]
 
    dates = date_pattern_4digit.findall(file_name[:20])
    if dates != []:
        if dates[0] > "1231":
            return ""
        else:
            return "2024"+dates[0]

    return ''
           
############### 옮겨진 파일 이름 변경하기 ##################
def rename_copied_file(ministry, file_name):
    split = os.path.splitext(file_name)
    file_name = split[0] + "-" + ministry + split[1]

    date_pattern_6digit = re.compile("\d{6}")
    date_pattern_4digit = re.compile("\d{4}")
    
    if date_pattern_6digit.findall(file_name) == []:
        d = date_pattern_4digit.findall(file_name)
        if d != []:
            file_name = file_name.replace(d[0], "23"+d[0])
        else:
            print("보도자료 날짜를 확인 할 수 없습니다.")

    file_name = file_name.replace("★", "").replace(",", "").replace("(보도참고자료)_", "")
    return file_name

############### 오래된 날짜 여부 확인하기 ##################
def check_date(deadline, year, month, day):
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(deadline)
    report_date = datetime.datetime(year, month, day)
    diff_date = report_date - start_date
    diff_days = diff_date.days
    
    if diff_days >= 0:
        return True
    else:
        return False

############### 파일 확장자 찾기 ##################
def find_file_index(eles):
    file_exts = [".hwpx", ".hwp", ".pdf"]
    for ext in file_exts:
        for i in range(len(eles)):
            if ext in eles[i].text:
                #print(i, eles[i].text)
                return i
    print(file_exts, "원하는 파일이 없습니다")
    
    return -1

############### 첨부 파일 정보 분석 ##################
def analyze_eles(eles, ix):
    ele_info = eles[ix].find_element("class name", "name").text
    temp = ele_info.split("[")
    file_name = temp[0].strip()

    if "MB" in temp[1]:
            file_size = float(temp[1].replace(" MB]", ""))
    else:
            file_size = 1

    link_info = eles[ix].find_element("class name", "link").find_elements("tag name", "a")
    for link in link_info:
        if "ODT" in link.text or "바로보기" in link.text:
            continue
        else:
            #print(link.text)
            link.click()
            time.sleep(1)     # 너무 빨리 넘어갈 경우 다운로드 진행여부 조차 확인 안됨
            
    return file_name

############### 첨부 파일 다운로드 ##################
def download_ele_ix (eles):
    temp = []
    file_size = []
    for i in range(len(eles)):
        temp.append(eles[i].text.split("[")[0].strip())
        if "MB" in eles[i].text:
            file_size.append(float(eles[i].text.split("[")[1].replace(" MB]", "")))
        else:
            file_size.append(1)
        
    file_exts = [".hwpx", ".hwp", ".pdf"]
    for ext in file_exts:    
        for i in range(len(temp)):
            if ext in temp[i]:
                return i, temp[i], file_size[i]

############### 다운로드 완료 기다리기 ##################
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

################# 보도자료 크롤링 시작 ###################
download_path = make_download_folder()
driver = start_webdriver(url_dict[ministry])
body = driver.find_element("css selector", 'body')

for next_10_pages_num in range(20):      # 20번 이번 충분하다고 판단(10 * 10 * 20개)
    if stop_program == True:
            print("프로그램을 종료합니다.")
            break
        
    for ix_page_num in range(9):            # 10개 페이지 반복(첫번째 페이지는 자동으로 선택)
        if stop_program == True:
            print("프로그램을 종료합니다.")
            break
        
        for i in range(articles_per_page):   # 한 페이지당 10개 보도자료 처리           
            current_news_release_info = []
            #time.sleep(1)
            
            ### 보도자료 제목 처리 ###
            title = ""
            
            try:
                total_cnt = total_cnt + 1
                
                xpath_title = f'//*[@id="contents_inner"]/div/table/tbody/tr[{i+1}]/td[2]/a'        #제목 element
                ele_title = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH, xpath_title)))
                title = ele_title.text

                xpath_num = f'//*[@id="contents_inner"]/div/table/tbody/tr[{i+1}]/td[1]'          #번호 element
                ele_num = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH, xpath_num)))
                num = int(ele_num.text)               
                
                xpath_department = f'//*[@id="contents_inner"]/div/table/tbody/tr[{i+1}]/td[3]'   #해당과 element
                ele_department = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH, xpath_department)))
                department = ele_department.text
                
                xpath_regdate = f'//*[@id="contents_inner"]/div/table/tbody/tr[{i+1}]/td[5]'   #등록일 element
                ele_regdate = WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH, xpath_regdate)))
                regdate = ele_regdate.text

                ele_title.click()
                print(total_cnt, num, regdate, title, f"({department})")
                
            except:
                error_report(driver, download_path, title)
                driver.back()
                continue
            current_news_release_info.append(num)                 ## 보도자료 번호
            current_news_release_info.append(title)                  ## 보도자료 제목 저장
            current_news_release_info.append(department)       ## 보도자료 소관과
            current_news_release_info.append(regdate)             ## 보도자료 등록일

            print(driver.current_url)
            if ONLY_NEW_FILES_DOWNLOAD == True and check_prev_download(download_files_info, driver.current_url) == False :
                print("기존에 이미 받은 자료이므로 프로그램을 종료합니다.")
                stop_program = True
                break
            
            ### 보도자료 첨부파일 다운로드 ###
            try:
                WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.CLASS_NAME, "file_list")))
            except:
                print("!!! 다운로드 error!!!")
                error_report(driver, download_path, title)
                driver.back()
                break
            
            eles = driver.find_element("class name", "file_list").find_elements("tag name", "li")
            download_index = find_file_index(eles)
            if download_index == -1:
                error_report(driver, download_path, title)
                driver.back()
                continue

            ### 다운로드된 첨부파일 분석  ###
            file_name = analyze_eles(eles, download_index)
            #print(file_name)

            file_date = get_date_from_filename(file_name)
            regist_date = driver.find_element("class name", "period").text.replace(".", "")
            regist_date = regist_date[2:]
            #print("등록 날짜는 ", regist_date)
            try:
                if file_date == "":
                    print("파일 날짜 처리중 에러 발생...!!")
                    print(default_download + "/" + file_name, default_download + "/" + regist_date +"_" + file_name)    
                    os.rename(default_download + "/" + file_name, default_download + "/" + regist_date +"_" + file_name) #2024수정 필
                    #print("변경된 파일명 : ", file_name)
                    file_name = regist_date +"_" + file_name
                    file_date = regist_date
            except:
                print("파일 날짜 정보 처리중 예외 발생....!!")
                error_report(driver, download_path, title)
                driver.back()
                continue

            ### 첨부파일 게시 날짜 확인 ###
            if len(regist_date) == 6:
                if check_date(DATECHECK_DEADLINE_DAYS, int(regist_date[0:2])+2000, int(regist_date[2:4]), int(regist_date[4:6])) == False:
                    #error_report(driver, download_path, title)
                    driver.back()
                    print("자료 수집 기한이 넘었습니다.!!")
                    stop_program = True
                    os.remove(default_download + "/" + file_name)
                    break
                
            ### 파일 다운로드 기다리기 ###
            try:
                download_wait(default_download, 300, nfiles=None)
            except:
                print("!!!!!!! 파일 다운로드 실패!!!!!!!")
                error_report(driver, download_path, title)
                driver.back()
                
            current_news_release_info.append(file_date)           ## 보도자료 배포 일자 저장
            time.sleep(1)

            ### 다운로드된 파일 이동 ###
            try:
                des_name = rename_copied_file(ministry, file_name)
                shutil.move(default_download+'/'+file_name, download_path + '/' + des_name)
            except:
                print("!!! 다운로드 파일 이동-move 실패 !!!")
                error_report(driver, download_path, title)
                driver.back()
                continue
            current_news_release_info.append(des_name)           ## 다운로드 파일명 저장
            current_news_release_info.append(driver.current_url)           ## 보도자료 url 저장
            
            ### 다운로드 파일명 및 URL 정보 저장 ###
            save_news_release_info(driver, download_path, [des_name, driver.current_url])
            news_release_all_info.append(current_news_release_info)      ## 현재 보도자료 정보 저장

            driver.back()
            time.sleep(1)

        ### 다음 페이지로 이동 ###
        if stop_program == True:
            print("stop_program == True")
            break
        else:
            xpath = f'//*[@id="contents_inner"]/div/div[4]/ul/li[{ix_page_num +2}]/a'
            ele = WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.XPATH, xpath)))
            ele.click()
            time.sleep(3)

    ### 다음 10개 페이지로 이동 ###
    if stop_program == True:
        print("stop_program == True")
        break
    else:
        xpath = '//*[@id="contents_inner"]/div/div[4]/a[3]'
        ele = WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.XPATH, xpath)))
        ele.click()
        time.sleep(3)
    
############## 최종 결과 엑셀로 정리하기 #########################
df = pd.DataFrame(news_release_all_info)
df.to_excel(download_path + "/" + "결과 정리.xlsx")
