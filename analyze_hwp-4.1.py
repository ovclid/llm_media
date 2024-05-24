import glob
import os
import time
import shutil  # 파일복사용 모듈
import win32com.client as win32  # 한/글 열기 위한 모듈
import pandas as pd  # 그 유명한 판다스. 엑셀파일을 다루기 위함
from datetime import datetime as dt  # 작업시간을 측정하기 위함. 지워도 됨.
import win32gui  # 한/글 창을 백그라운드로 숨기기 위한 모듈
import re

date_pattern = re.compile("\d{6}")

base_dri = "./hwp_files/"
files = glob.glob("./hwp_files/*.*")
files = [file.replace("\\", "/") for file in files]
dates = [date_pattern.findall(file) for file in files]

#'일상의 코딩' - 파이썬 + 한컴오피스 자동화 : 누름틀없는 대량의 한글문서를 엑셀에 취한하는 라이브코
def find_keyword(hwp, keyword):
    hwp.HAction.GetDefault("RepeatFind", hwp.HParameterSet.HFindReplace.HSet)
    hwp.HParameterSet.HFindReplace.Direction = hwp.FindDir("Forward")
    hwp.HParameterSet.HFindReplace.FindString = keyword
    hwp.HParameterSet.HFindReplace.IgnoreMessage = 1
    hwp.HParameterSet.HFindReplace.FindType = 1
    status = hwp.HAction.Execute("RepeatFind", hwp.HParameterSet.HFindReplace.HSet)
    
    return status

def insertText(hwp, text):
    act = hwp.CreateAction("InsertText")
    pset = act.CreateSet()
    pset.SetItem("Text", text)
    act.Execute(pset)
    
def SetTableCellAddr(addr):
    init_addr = hwp.KeyIndicator()[-1][1:].split(")")[0]  # 함수를 실행할 때의 주소를 기억.
    if not hwp.CellShape:  # 표 안에 있을 때만 CellShape 오브젝트를 리턴함
        raise AttributeError("현재 캐럿이 표 안에 있지 않습니다.")
    if addr == hwp.KeyIndicator()[-1][1:].split(")")[0]:  # 시작하자 마자 해당 주소라면
        return  # 바로 종료
    hwp.Run("CloseEx")  # 그렇지 않다면 표 밖으로 나가서
    hwp.FindCtrl()  # 표를 선택한 후
    hwp.Run("ShapeObjTableSelCell")  # 표의 첫 번째 셀로 이동함(A1으로 이동하는 확실한 방법 & 셀선택모드)
    while True:
        current_addr = hwp.KeyIndicator()[-1][1:].split(")")[0]  # 현재 주소를 기억해둠
        hwp.Run("TableRightCell")  # 우측으로 한 칸 이동(우측끝일 때는 아래 행 첫 번째 열로)
        if current_addr == hwp.KeyIndicator()[-1][1:].split(")")[0]:  # 이동했는데 주소가 바뀌지 않으면?(표 끝 도착)
            # == 한 바퀴 돌았는데도 목표 셀주소가 안 나타났다면?(== addr이 표 범위를 벗어난 경우일 것)
            SetTableCellAddr(init_addr)  # 최초에 저장해둔 init_addr로 돌려놓고
            hwp.Run("Cancel")  # 선택모드 해제
            raise AttributeError("입력한 셀주소가 현재 표의 범위를 벗어납니다.")
        if addr == hwp.KeyIndicator()[-1][1:].split(")")[0]:  # 목표 셀주소에 도착했다면?
            return  # 함수 종료

# 표의 모든 셀을 순회하면서 텍스트를 추출하여 리스트 형태로 반환하는 함수
def get_HWPTableText(hwp, table_ctrl):
    #print("start get_HWPTableText!!!!!!")
    hwp.SetPosBySet(table_ctrl.GetAnchorPos(0))   # 표 바로 앞으로 세팅
    hwp.FindCtrl()
    hwp.Run("ShapeObjTableSelCell")   # 표의 첫번째 셀 선택

    
    content = []
    while True:
        #print("hwp.InitScan(Range = 0x00ff)")
        hwp.InitScan(Range = 0x00ff)  # 스캔 범위 설정 0x00ff -> 블록
        total_text = ""
        state = 2   # 0, 1 만 아니면 상관없음
        while state not in [0, 1]:
            state, text= hwp.GetText()   # 한글 특수문자 인식 못함 (프린트 에러)
            #print(state, text)
            total_text += text

        #print(total_text)
        total_text = total_text.replace("\r\n", " ")
        #print(total_text)
        content.append(total_text)

        if hwp.HAction.Run("TableRightCell") != True:   # 표의 모든 셀을 순회 했다면
            return content
            break

# 한글 문서에서 표 컨트롤러들을 리스트 형태로 반환하는 함수
def find_HWPTableCtrl(hwp):   
    current_ctrl = hwp.HeadCtrl     # 첫번째 컨트롤러로 세팅
    tableCtrl = []
    while current_ctrl != None:
        #print(current_ctrl.CtrlID)      
        if current_ctrl.CtrlID  == "tbl" :
            #print("테이블 컨트롤러를 찾았습니다")
            tableCtrl.append(current_ctrl)

        next_ctrl = current_ctrl.Next  # 다음 컨트롤러로 세팅
        current_ctrl = next_ctrl

    return tableCtrl

def deleteTables(hwp, table_ctrls):
    for i, ctrl in enumerate(table_ctrls):
        try:
            hwp.SetPosBySet(ctrl.GetAnchorPos(0))
            hwp.Run("MoveSelRight")
            hwp.Run("Delete")
        except:
            print(f"{i+1} 표 삭제 과정에서 에러 발생")
            
def find_charger_ix(table_total_info):
    for i in range(len(table_total_info)):
        if table_total_info[i][0].strip().replace(" ", "") == "담당부서":
            for j in range(len(table_total_info[i])):
                table_total_info[i][j] = table_total_info[i][j].strip().replace(" ", "")
            return i

    return -1

hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
hwp.XHwpWindows.Item(0).Visible = True
hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")

for file in files:
    cwd = os.getcwd().replace("\\", "/")
    hwp.Open(cwd + file)
    
    table_ctrls = find_HWPTableCtrl(hwp)
    table_total_info = []
    
    for ctrl in table_ctrls:
        table_info = get_HWPTableText(hwp, ctrl)
        table_total_info.append(table_info)

    #print(table_ctrls)
    if len(table_ctrls) >= 4:
        for i in range(len(table_total_info)):
            #print(table_total_info[i][0])

            
            if table_total_info[i][0].strip().replace(" ", "") == "담당부서":
            #if table_total_info[i][0].strip().replace(" ", "") == "참고":        ##### 이전 양식
                
                hwp.SetPosBySet(table_ctrls[i].GetAnchorPos(0))
                hwp.Run("MoveSelDocEnd")
                hwp.Run("Delete")

        table_ctrls = find_HWPTableCtrl(hwp)   # 표 컨트롤러 다시 찾기
        deleteTables(hwp, table_ctrls)

        pure_content  = ""
        for i in range(hwp.PageCount):
            pure_content += hwp.GetPageText(i)
            
        pure_content = pure_content.strip().replace("\r\n", "\n").replace("\n\n", "\n")
        #print(pure_content)  #\uf083 U000f02b3 특수문자 프린트시 에러(멈춤)

        try:
            if table_total_info[0][1] != '':
                table_total_info[0][1] = table_total_info[0][1].replace(" ", "")
        
            add_info = f"\n\n위 내용은 {table_total_info[0][0].strip()} {table_total_info[0][1]}로 "
        except:
            print("replace error", table_total_info[0])
            add_info = ''
                       
        press_dates = date_pattern.findall(file)
        press_date = ''
        if press_dates != []:
            press_date = '20' + press_dates[0][:2] + '년 ' + press_dates[0][2:4] + '월 ' + press_dates[0][4:6] + '일'
            add_info += f"{press_date}에 배포되었습니다."

        
                    
        add_info +=  f"\n제목은 '{table_total_info[2][0].strip()}' 입니다. "  ##### 새로운 양식

        if len(table_total_info[2]) == 2:
            add_info +=  f"\n간단히 요약하면 '{table_total_info[2][1].strip()}'입니다."
        
        charger = find_charger_ix(table_total_info)
        if charger != -1:
            print(table_total_info[charger])
            print(int(len(table_total_info[charger]) / 6))
            if int(len(table_total_info[charger]) / 6) >= 2:
                add_info += f"\n담당자는 {table_total_info[charger][1]} {table_total_info[charger][7]}의 {table_total_info[charger][10]} {table_total_info[charger][9]}으로, 연락처는 {table_total_info[charger][11]} 입니다"
            else:
                add_info += f"\n담당자는 {table_total_info[charger][1]}의 {table_total_info[charger][4]} {table_total_info[charger][3].replace(' ','')}으로, 연락처는 {table_total_info[charger][5]} 입니다."
        else:
            print("담당자 정보를 찾지 못했습니다...!!")
        
        
        add_info += f"\n-- end --"

        print(add_info)


        if file.endswith(".hwp") :
            new_file = file.replace(".hwp", ".txt")
        elif file.endswith(".hwpx") :
            new_file = file.replace(".hwpx", ".txt")
        else:
            print(file, "파일 형식이 다릅니다")
            hwp.XHwpDocuments.Item(0).Close(isDirty=False)
            continue
        f = open(new_file, "w", encoding = "utf-8")
        f.write(pure_content)
        f.write(add_info)
        f.close()
         
    else:
        print("규정된 보도자료 양식이 아닙니다..")
    
    #input("문서를 저장하지 않고 닫겠습니까??")
    hwp.XHwpDocuments.Item(0).Close(isDirty=False)

hwp.Quit()

"""	
for file in files:
    hwp.Open(cwd + file[1:])
    print(file, hwp.PageCount)
    hwp.MovePos(2) # 문서 처음으로 이동하

    hwp.Run("SelectAll")
    hwp.Run("Copy")


    print("문서 종료중....")
    time.sleep(3)

    hwp.HAction.Run("FileClose")
"""

#hwp.Quit()
#result_hwp.Save()
#result_hwp.Quit()
