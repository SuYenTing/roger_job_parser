import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 讀取Line Tokens
lineToken = os.environ['LINE_TOKEN']

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
outputData = outputData[~outputData['職務列等/職系'].str.contains('土木工程職系|經建行政')]

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
    jobRestrict = any([True if elem in jobDescription else False for elem in ['限制轉調', '限制調任', '身心障礙']])

    # 紀錄資訊
    outputData.loc[ix, '是否限制資格'] = jobRestrict

# 篩掉有限制資格之職缺
outputData = outputData[~outputData['是否限制資格']]

# 重新排序編號
outputData = outputData.reset_index(drop=True)

# Line Notify設定
url = 'https://notify-api.line.me/api/notify'
headers = {
    'Authorization': 'Bearer ' + lineToken
}

# 建立訊息模板
def msgTemplate(data):

    msg = '\n'.join([
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