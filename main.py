import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import re
import json


################### 參數設定 ###################
# 職缺類別過濾名單
jobTypeFilterList = [
    '土木工程', '經建行政', '資訊處理', '財稅金融', 
    '建築工程', '衛生行政', '電機工程', '衛生技術',
    '地政', '會計審計',
    ]

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

# 篩選所需欄位
outputData = outputData[[
    '職缺來源', '徵才機關', '登載日期', '人員類別', '職稱', 
    '職務列等/職系', '職缺連結']]


# ################### 事求人機關徵才系統 ###################
# # 目標網址
# url = 'https://web3.dgpa.gov.tw/WANT03FRONT/AP/WANTF00003.aspx?GETJOB=Y'
# response = requests.get(url)
# soup = BeautifulSoup(response.text, 'xml')

# # 整理資料
# iOutputData = pd.DataFrame(
#     data={
#         '職缺地點': soup.find_all('WORK_PLACE_TYPE'),
#         '徵才機關': soup.find_all('ORG_NAME'),
#         '登載起始日': soup.find_all('DATE_FROM'),
#         '登載結束日': soup.find_all('DATE_TO'),
#         '人員類別': soup.find_all('PERSON_KIND'),
#         '職稱': soup.find_all('TITLE'),
#         '職務列等': soup.find_all('RANK'),
#         '職務職系': soup.find_all('SYSNAM'),
#         '資格條件': soup.find_all('WORK_QUALITY'),
#         '工作項目': soup.find_all('WORK_ITEM'),
#         '聯絡方式': soup.find_all('CONTACT_METHOD'),
#         '職缺連結': soup.find_all('VIEW_URL'),
#     }   
# )
# iOutputData = iOutputData.explode(list(iOutputData.columns))

# # 篩選地區
# iOutputData = iOutputData[iOutputData['職缺地點'].str.contains('臺南市', na=False)]

# # 篩選職務
# iOutputData = iOutputData[iOutputData['職務列等'].str.contains('委任', na=False)]
# iOutputData = iOutputData[iOutputData['職務列等'] != '委任第1職等待遇至委任第3職等待遇']
# iOutputData = iOutputData[~iOutputData['職務職系'].str.contains('|'.join(jobTypeFilterList))]
# iOutputData = iOutputData[~iOutputData['資格條件'].str.contains('|'.join(jobRestrictFilterList))]
# iOutputData = iOutputData[~iOutputData['工作項目'].str.contains('|'.join(jobRestrictFilterList))]
# iOutputData = iOutputData[~iOutputData['聯絡方式'].str.contains('|'.join(jobRestrictFilterList))]

# # 整理職缺地點
# iOutputData['職缺地點'] = iOutputData['職缺地點'].apply(lambda x: ','.join(re.findall(r'\d+-(.*?)(?=,|\Z)', x)))

# # 整理日期
# iOutputData['登載起始日'] = (iOutputData['登載起始日'].astype('int')+19110000).astype('str')
# iOutputData['登載起始日'] = iOutputData['登載起始日'].apply(lambda x: x[:4] + '/' + x[4:6] + '/' + x[6:])
# iOutputData['登載結束日'] = (iOutputData['登載結束日'].astype('int')+19110000).astype('str')
# iOutputData['登載結束日'] = iOutputData['登載結束日'].apply(lambda x: x[:4] + '/' + x[4:6] + '/' + x[6:])
# iOutputData['登載日期'] = iOutputData['登載起始日'] + ' ~ ' + iOutputData['登載結束日']

# # 整理職務列等/職系
# iOutputData['職務列等/職系'] = iOutputData['職務列等'] + ' / ' + iOutputData['職務職系']

# # 加入資料來源
# iOutputData.insert(0, '職缺來源', '事求人')

# # 篩選所需欄位
# iOutputData = iOutputData[[
#     '職缺來源', '徵才機關', '登載日期', '人員類別', '職稱', 
#     '職務列等/職系', '職缺連結']]

# # 合併資料
# outputData = pd.concat([outputData, iOutputData])


################### 人事行政總處事求人開放資料版 ###################
# 取得資料
url = 'https://dgpajobs.net/'
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')
data = soup.find_all('script')[5].text
data = data.split('var ')[1]
data = data.strip()
data = data.replace('jobdata = ', '')
data = json.loads(data)

# 整理資料
data = pd.DataFrame(
    data={
        '職缺地點': [elem['fields']['work_places_id'] for elem in data],
        '徵才機關': [elem['fields']['org_name'] for elem in data],
        '登載起始日': [elem['fields']['date_from'] for elem in data],
        '登載結束日': [elem['fields']['date_to'] for elem in data],
        '人員類別': [elem['fields']['person_kind'] for elem in data],
        '職稱': [elem['fields']['title'] for elem in data],
        '職務列等起始': [elem['fields']['rank_from'] for elem in data],
        '職務列等結束': [elem['fields']['rank_to'] for elem in data],
        '職務列等': [elem['fields']['job_type'] for elem in data],
        '職務職系': [elem['fields']['sysnam'] for elem in data],
        '資格條件': [elem['fields']['work_quality'] for elem in data],
        '工作項目': [elem['fields']['work_item'] for elem in data],
        '聯絡方式': [elem['fields']['contact'] for elem in data],
        '職缺連結': [elem['fields']['view_url'] for elem in data],
    }   
)

# 篩選地區
data = data[data['職缺地點'].str.contains('72', na=False)]

# 整理登載日期
data['登載日期'] = data['登載起始日'] + ' ~ ' + data['登載結束日']

# 篩選職務
data = data[data['職務列等'].str.contains('委任', na=False)]
data = data[data['職務列等起始'] >= 3]
data = data[~data['職務職系'].str.contains('|'.join(jobTypeFilterList))]
data = data[~data['資格條件'].str.contains('|'.join(jobRestrictFilterList))]
data = data[~data['工作項目'].str.contains('|'.join(jobRestrictFilterList))]
data = data[~data['聯絡方式'].str.contains('|'.join(jobRestrictFilterList))]

# 整理職務列等/職系
data['職務列等/職系'] = data['職務列等起始'].astype('str') +\
      '-' + data['職務列等結束'].astype('str') +\
          ' 職等 / ' + data['職務職系']

# 加入資料來源
data.insert(0, '職缺來源', '事求人開放資料版')

# 篩選所需欄位
data = data[[
    '職缺來源', '徵才機關', '登載日期', '人員類別', '職稱', 
    '職務列等/職系', '職缺連結']]

# 合併資料
outputData = pd.concat([outputData, data])
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