import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import re


################### 參數設定 ###################
# 職缺類別過濾名單
jobTypeFilterList = ['土木工程', '經建行政', '資訊處理', '財稅金融', '建築工程', '衛生行政', '電機工程', '衛生技術']

# 限制資格字詞
jobRestrictFilterList = ['限制轉調', '限制調任', '身心障礙']


################### 台南市政府徵才專區爬蟲 ###################
# 台南市政府徵才專區
url = 'https://personnel.tainan.gov.tw/listRecruit.aspx?nsub=K0A410'
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# 取得職缺列
jobs = soup.find_all('tr')

# 刪去標題
jobs = jobs[1:]

# 迴圈整理職缺資訊
ix = 0
outputData = list()
for ix in range(len(jobs)):
    iData = [elem.getText() for elem in jobs[ix].find_all('td')]
    iLink = ['https://personnel.tainan.gov.tw/' + jobs[ix].find_all('a')[0]['href']]
    iData = iData + iLink
    outputData.append(iData)

# 彙整數據
outputData = pd.DataFrame(outputData, columns=['徵才機關', '登載日期', '人員類別', '職稱', '職務列等/職系', '名額', '工作地點', '職缺連結'])

# 移除空白格字元
for column in outputData.columns:
    outputData[column] = outputData[column].str.strip()

# 篩選委任職缺
outputData = outputData[outputData['職務列等/職系'].str.contains('委任')]

# 過濾掉不符合的職系(負面表列)
outputData = outputData[~outputData['職務列等/職系'].str.contains('|'.join(jobTypeFilterList))]

# 重新排序編號
outputData = outputData.reset_index(drop=True)

# 建立轉調/身心障礙限制欄位
outputData['是否限制資格'] = bool()

# 進一步搜尋職缺詳細資訊
ix = 0
for ix in range(len(outputData)):

    time.sleep(1)

    # 取得職缺詳細資訊
    url = outputData['職缺連結'].iloc[ix]
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 判斷是否有限制資格
    jobDescription = soup.find_all('td')
    jobDescription = [elem.getText() for elem in jobDescription]
    jobDescription = ' '.join(jobDescription)
    jobRestrict = any([True if elem in jobDescription else False for elem in jobRestrictFilterList])

    # 紀錄資訊
    outputData.loc[ix, '是否限制資格'] = jobRestrict

# 篩掉有限制資格之職缺
outputData = outputData[~outputData['是否限制資格']]

# 重新排序編號
outputData = outputData.reset_index(drop=True)

# 加入資料來源
outputData.insert(0, '職缺來源', '台南市政府')


################### 事求人機關徵才系統 ###################
# 目標網址
url = 'https://web3.dgpa.gov.tw/want03front/AP/WANTF00001.ASPX'

# 查詢期間參數
edDateTime = datetime.now().strftime('%Y/%m/%d')
stDateTime = (datetime.now() - timedelta(days=7)).strftime('%Y/%m/%d')
edDateTime = str(int(edDateTime[0:4])-1911)+edDateTime[4:11]
stDateTime = str(int(stDateTime[0:4])-1911)+stDateTime[4:11]

# 發送 POST 請求
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# 取得viewstate參數
viewstate = soup.find('input', {'name': '__VIEWSTATE'}).get('value')

# POST 請求參數
payload = {
    '__EVENTTARGET': '',
    '__EVENTARGUMENT': '',
    '__LASTFOCUS': '',
    '__VIEWSTATE': viewstate,
    '__VIEWSTATEGENERATOR': 'B32C3998',
    '__VIEWSTATEENCRYPTED': '',
    'ctl00$ContentPlaceHolder1$drpPERSON_KIND': '',
    'ctl00$ContentPlaceHolder1$drpWORK_PLACE': '72',
    'ctl00$ContentPlaceHolder1$txtTITLE': '',
    'ctl00$ContentPlaceHolder1$txtSYSNAM': '',
    'ctl00$ContentPlaceHolder1$txbORG_NAME': '',
    'ctl00$ContentPlaceHolder1$DATE_FROM': stDateTime,
    'ctl00$ContentPlaceHolder1$DATE_TO': edDateTime,
    'ctl00$ContentPlaceHolder1$chkTYPE3': 'on',
    'ctl00$ContentPlaceHolder1$btnQUERY': '查詢',
    'ctl00$ContentPlaceHolder1$ddl_Sort': 'DATE_FROM_DESC',
    'ctl00$ContentPlaceHolder1$ddlCOUNT': '1',
    'ctl00$ContentPlaceHolder1$txtPAGE_SIZE': '99',
}

# 發送 POST 請求
response = requests.post(url, data=payload)
soup = BeautifulSoup(response.text, 'html.parser')

# 取得職缺資訊
links = soup.findAll('div', id=re.compile('ctl00_ContentPlaceHolder1_gvMAIN*'))
links = [elem.get('onclick').split("'")[1] for elem in links]
links = ['https://web3.dgpa.gov.tw/want03front/AP/'+ elem for elem in links]


# 迴圈連結
for link in links:

    time.sleep(1)

    # 發送Get請求
    response = requests.get(link)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 取得相關資訊
    jobInfo = [elem.get_text() for elem in soup.find_all(class_='job_detail_item_content')]

    # 過濾不符合職缺
    checks = [True if jobType in jobInfo[3] else False for jobType in jobTypeFilterList]
    if any(checks):
        continue

    # 過濾限制資格字詞
    allJobInfo = ' '.join(jobInfo)
    checks = [True if jobRestrict in allJobInfo else False for jobRestrict in jobRestrictFilterList]
    if any(checks):
        continue

    # 取得職稱
    iOutputData = pd.DataFrame(
        data={
            '職缺來源': '事求人',
            '徵才機關': soup.find(class_='job_detail_item_content').get_text(),
            '登載日期': jobInfo[7],
            '人員類別': jobInfo[1],
            '職稱': jobInfo[0], 
            '職務列等/職系': jobInfo[2] + ' / ' + jobInfo[3], 
            '名額': jobInfo[4], 
            '工作地點': jobInfo[6], 
            '職缺連結': link,
            '是否限制資格': False,
        }, 
        index=[0]
    )
    
    # 合併資料
    outputData = pd.concat([outputData, iOutputData])
    
# 重設Index
outputData = outputData.reset_index(drop=True)


################### 發送Line ###################
# 讀取Line Tokens
lineToken = os.environ['LINE_TOKEN']

# Line Notify設定
url = 'https://notify-api.line.me/api/notify'
headers = {
    'Authorization': 'Bearer ' + lineToken
}

# 建立訊息模板
def msgTemplate(data):

    msg = '\n'.join([
        f'職缺來源: {data["職缺來源"]}',
        f'徵才機關: {data["徵才機關"]}',
        f'登載日期: {data["登載日期"]}',
        f'人員類別: {data["人員類別"]}',
        f'職稱: {data["職稱"]}',
        f'職務列等/職系: {data["職務列等/職系"]}',
        f'職缺連結: {data["職缺連結"]}',
    ])

    return msg

# 推播Line訊息
if len(outputData) == 0:

    # 本日無符合職缺
    data = {
        'message': '\n'.join([
            datetime.now().strftime('%Y-%m-%d'),
            '本日無符合職缺'
        ])
    }
    res = requests.post(url, headers=headers, data=data)

else:

    data = {
        'message': '\n'.join([
            datetime.now().strftime('%Y-%m-%d'),
            f'本日共篩選到{len(outputData)}檔符合條件之職缺',
        ])
    }
    res = requests.post(url, headers=headers, data=data)

    # 迴圈推送職缺資訊
    for ix in range(len(outputData)):

        data = msgTemplate(outputData.iloc[ix])
        data = {
            'message': f'第{ix+1}個職缺資訊:\n'+data,
        }
        res = requests.post(url, headers=headers, data=data)