import subprocess
import os
import sys
import shutil

""" 수정 필요 '"""
answser = input("리눅스에 txt 폴더 내용을 모두 지울까요?(y/n) ")
if answser.upper() == "Y":
    print(subprocess.check_call(['wsl', "rm","~ssha08/project/llm_media/data/sub/*.txt"]))
else:
    print("프로그램을 종료합니다")
    sys.exit()
    
answser = input("윈도우 txt 파일들을 리눅스에 복사할까요?(y/n) ")
if answser.upper() == "Y":
    print(subprocess.check_call(['wsl', "cp","/mnt/c/python/hwp_files/*.txt", "~ssha08/project/llm_media/data/sub"]))
else:
    print("프로그램을 종료합니다")
    sys.exit()

answser = input("리눅스에 복사된 txt 파일들을 chromaDB화 할까요?(y/n) ")
if answser.upper() == "Y":
    #print(subprocess.check_call(['wsl', 'python3', '~ssha08/project/llm_media/manipulate.py']))
    print(subprocess.check_call(['wsl', 'python3', '~ssha08/project/llm_media/test.py']))
else:
    print("프로그램을 종료합니다")
    sys.exit()

answser = input("윈도우즈의 기존 chroma DB를 삭제할까요?(y/n) ")
if answser.upper() == "Y":
    shutil.rmtree("c:/python/chroma/main")
else:
    print("프로그램을 종료합니다")
    sys.exit()

answser = input("리눅스의 chromaDB를 윈도우즈로 복사할까요?(y/n) ")
if answser.upper() == "Y":
    print(subprocess.check_call(['wsl', "cp", "-r", "~ssha08/project/llm_media/chroma/main", "/mnt/c/python/chroma"]))
else:
    print("프로그램을 종료합니다")
    sys.exit()
    


"""

def callps1():
    powerShellPath = r'C:\WINDOWS\system32\WindowsPowerShell\v1.0\powershell.exe'
    powerShellCmd = "./script.ps1"
    #call script with argument '/mnt/c/Users/aaa/'
    p = subprocess.Popen([powerShellPath, '-ExecutionPolicy', 'Unrestricted', powerShellCmd, '/mnt/c/Users/aaa/', 'SecondArgValue']
                         , stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate()
    rc = p.returncode
    print("Return code given to Python script is: " + str(rc))
    print("\n\nstdout:\n\n" + str(output))
    print("\n\nstderr: " + str(error))


# Test
callps1()
"""

