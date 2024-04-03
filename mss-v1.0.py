from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.action_chains import ActionChains
import time, datetime, os, subprocess
import openpyxl
import re, shutil
import pathlib

import ss_source_file_update as ssup
import ss_auto_chromedriver as ssdriver

def error_report(driver, download_path, title):
    f = open(f"{download_path}/!!!_다운로드 에러_!!!.txt", "a", encoding = "utf-8")
    f.write(driver.current_url + "\n")
    f.write(title + "\n\n")
    f.close()

def save_news_release_info(driver, download_path, current_news_release_info):
    file_name = ""
    url_link = ""

    for info in current_news_release_info:
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
    
def start_webdriver(url):    
    #serv = Service("C:/chromedriver/chromedriver.exe")
    #serv.creation_flags = subprocess.CREATE_NO_WINDOW   
    #driver = webdriver.Chrome(service = serv)

    driver = ssdriver.start()
    
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
           
    
def rename_copied_file(department, file_name):
    split = os.path.splitext(file_name)
    file_name = split[0] + "-" + department + split[1]

    date_pattern_6digit = re.compile("\d{6}")
    date_pattern_4digit = re.compile("\d{4}")
    
    if date_pattern_6digit.findall(file_name) == []:
        d = date_pattern_4digit.findall(file_name)
        if d != []:
            file_name = file_name.replace(d[0], "23"+d[0])
        else:
            print("보도자료 날짜를 확인 할 수 없습니다.")

    return file_name



def check_date(year, month, day):
    past_days = 160                          # 160일 전까지 유효
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(past_days)

    print(start_date, end_date)
    report_date = datetime.datetime(year, month, day)

    print(report_date)
    diff_date = report_date - start_date
    diff_days = diff_date.days
    
    if diff_days >= 0:
        return True
    else:
        return False
    

url_dict = {
    "중소벤처기업부" : "https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=86",
}

#default_download = "C:/Users/smba/Downloads"
default_download = str(pathlib.Path.home() / "Downloads")
department = "중소벤처기업부"

driver = start_webdriver(url_dict[department])
download_path = make_download_folder()

total_articles = 15  # 테스트
articles_per_page = 10
page_nums = int(total_articles / articles_per_page) + 1

body = driver.find_element("css selector", 'body')

"""
for i in range(1):
    body.send_keys(Keys.PAGE_DOWN)

"""

"""
def download_attachedFiles():
    global driver

    file_ele = driver.find_elements("class name", "btn.type_down")
    file_name_ele = driver.find_elements("class name", "name")
    
    for ix_file in range(len(file_ele)):
        file_name = file_name_ele[ix_file].text.split(" ")[0]
        print(file_name)
        file_ele[ix_file].click()
        time.sleep(3)
"""
def find_file_index(eles):
    file_exts = [".hwpx", ".hwp", ".pdf"]
    for ext in file_exts:
        for i in range(len(eles)):
            if ext in eles[i].text:
                print(i, eles[i].text)
                return i
    print(file_exts, "원하는 파일이 없습니다")
    
    return -1

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
            print(link.text)
            link.click()
            time.sleep(1)     # 너무 빨리 넘어갈 경우 다운로드 진행여부 조차 확인 안됨
            
    return file_name
        
    
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
        print(ext)
    
        for i in range(len(temp)):
            if ext in temp[i]:
                print(temp[i])
                return i, temp[i], file_size[i]
            
    """
    ele_ix = 0

    file_name = ''
    for i in range(len(eles)):
        temp = eles[i].text.split("[")[0].strip()
        print(temp)
        file_ext = os.path.splitext(temp)[-1]
        print(file_ext)
        if file_ext == ".hwpx":
            return [ele_ix, temp]
        elif file_ext == ".hwp":
            ele_ix = i
            file_name = temp
    
    return [ele_ix, file_name]
    """
    
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


news_release_all_info = []
stop_program = False

file_ext = ('.hwp', '.hwpx',  '.pdf', '.xlsx', '.ppt', '.pptx', '.doc', 'docx', '.png', '.jpg', '.jpeg')
for next_10_pages_num in range(20):
    print("next_10_pages_num", next_10_pages_num)
    if stop_program == True:
            print("프로그램을 종료합니다.")
            break
        
    for ix_page_num in range(9):
        if stop_program == True:
            print("프로그램을 종료합니다.")
            break
        
        print("ix_page_num", ix_page_num)
        for i in range(articles_per_page):
            current_news_release_info = []
            time.sleep(1)
            title = ""

            print("try to find the title")
            xpath = f'//*[@id="contents_inner"]/div/table/tbody/tr[{i+1}]/td[2]/a'   #해당 제목 element
            #ele = driver.find_element("xpath", xpath)
            try:
                ele = WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.XPATH, xpath)))
                title = ele.text
                ele.click()
            except:
                error_report(driver, download_path, title)
                driver.back()
                continue
            current_news_release_info.append(title)                  ## 보도자료 제목 저장
            
            print("try to download the files")
            try:
                WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.CLASS_NAME, "file_list")))
            except:
                print("!!! 다운로드 error!!!")
                error_report(driver, download_path, title)
                driver.back()
                continue
                
            eles = driver.find_element("class name", "file_list").find_elements("tag name", "li")
            download_index = find_file_index(eles)
            if download_index == -1:
                error_report(driver, download_path, title)
                driver.back()
                continue
            
            file_name = analyze_eles(eles, download_index)
            print(file_name)
            
            
            #file_ele = driver.find_elements("class name", "btn.type_down")
            #file_name_ele = driver.find_elements("class name", "name")
            
            #file_ix, file_name, file_size = download_ele_ix (file_name_ele)
            #print(file_ix, file_name, file_size)

            file_date = get_date_from_filename(file_name)
            regist_date = driver.find_element("class name", "period").text.replace(".", "")
            regist_date = regist_date[2:]
            print("등록 날짜는 ", regist_date)
            try:
                if file_date == "":
                    print("파일 데이트 에러")
                    print(default_download + "/" + file_name, default_download + "/" + regist_date +"_" + file_name)    
                    os.rename(default_download + "/" + file_name, default_download + "/" + regist_date +"_" + file_name) #2024수정 필
                    print("변경된 파일명 : ", file_name)
                    file_name = regist_date +"_" + file_name
                    file_date = regist_date
            except:
                print("파일 날짜 정보 처리중 예외 발생....!!")
                error_report(driver, download_path, title)
                driver.back()
                continue

            if len(regist_date) == 6:
                print("날짜를 확인합니다...")
                
                if check_date(int(regist_date[0:2])+2000, int(regist_date[2:4]), int(regist_date[4:6])) == False:
                    #error_report(driver, download_path, title)
                    driver.back()
                    print("수집하고자하는 기한이 넘었어 중단합니다.!!")
                    stop_program = True
                    break
            
            #file_ele[file_ix].click()
            try:
                download_wait(default_download, 300, nfiles=None)
            except:
                print("!!!!!!! 파일 다운로드 실패!!!!!!!")
                error_report(driver, download_path, title)
                driver.back()
                
            current_news_release_info.append(file_date)           ## 보도자료 배포 일자 저장
            time.sleep(1)
            
            """
            if file_size >= 10:
                time.sleep(10)
            else:
                time.sleep(5)
            """
            try:
                des_name = rename_copied_file(department, file_name)
                shutil.move(default_download+'/'+file_name, download_path + '/' + des_name)
            except:
                print("!!! 다운로드 파일 이동-move 실패 !!!")
                error_report(driver, download_path, title)
                driver.back()
                continue
            current_news_release_info.append(des_name)           ## 다운로드 파일명 저장
            
            """
            for ix_file in range(len(file_ele)):
                file_name = file_name_ele[ix_file].text.split(" ")[0]
                print(file_name)
                if file_name.lower().endswith(file_ext):
                    file_ele[ix_file].click()
                    time.sleep(3)

                    des_name = rename_copied_file(department, file_name)
                    
                    shutil.move(default_download+'/'+file_name, download_path + '/' + des_name)
                    
                else :
                    print("첨부파일 형태가 아닙니다")
            """

            current_news_release_info.append(driver.current_url)           ## 보도자료 url 저장
            driver.back()
            time.sleep(1)

            print(current_news_release_info)                                      ## 현재 보도자료 정보 출력
            save_news_release_info(driver, download_path, current_news_release_info)
            news_release_all_info.append(current_news_release_info)      ## 현재 보도자료 정보 저장
            
        xpath = f'//*[@id="contents_inner"]/div/div[4]/ul/li[{ix_page_num +2}]/a'
        #ele = driver.find_element("xpath", xpath)
        ele = WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.XPATH, xpath)))
        ele.click()
        time.sleep(3)
        
    xpath = '//*[@id="contents_inner"]/div/div[4]/a[3]'
    #ele = driver.find_element("xpath", next_10_xpath)
    ele = WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.XPATH, xpath)))
    ele.click()
    time.sleep(3)
    

import pandas as pd
df = pd.DataFrame(news_release_all_info)
df.to_excel("결과 정리.xlsx")

'''
for ix_page_num in range(page_nums):    
    cnt = 0
    for i in range(articles_per_page):
        eles = driver.find_elements("class name", "subject")
        print(eles[cnt].text)
        eles[cnt].click()
        time.sleep(5)
        
        file_ele = driver.find_elements("class name", "btn.type_down")
        file_name_ele = driver.find_elements("class name", "name")
        for ix_file in range(len(file_ele)):
            file_name = file_name_ele[ix_file].text.split(" ")[0]
            print(file_name)
            file_ele[ix_file].click()
            time.sleep(3)
            
        driver.back()
        cnt += 1
        time.sleep(2)
    #for ix_article in range(articles_per_page):
'''        
