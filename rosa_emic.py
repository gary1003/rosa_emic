from EMIC_crawler import CrawlerEMIC
import boto3
import pandas as pd
import os
import sqlite3
from uuid import uuid4
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from datetime import datetime
import sys
# keep last 200 lines of log
with open(os.path.join(os.path.dirname(__file__), 'log.txt'), 'r', encoding='utf-8') as f:
    lines = f.readlines()
with open(os.path.join(os.path.dirname(__file__), 'log.txt'), 'w', encoding='utf-8') as f:
    f.writelines(lines[-200:])

# redirect stdout to file
sys.stdout = open(os.path.join(os.path.dirname(__file__), 'log.txt'), 'a', encoding='utf-8')
sys.stderr = open(os.path.join(os.path.dirname(__file__), 'log.txt'), 'a', encoding='utf-8')

load_dotenv()
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
last_update_file = os.path.join(os.path.dirname(__file__), 'last_update.txt')
local_db = os.path.join(os.path.dirname(__file__), 'emic.sqlite')

class DynamoDBChecker:

    def __init__(self, table_name='data_dmm_to_rosa'):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')
        self.table = self.dynamodb.Table(table_name)
        self.database = sqlite3.connect(local_db)

    def __del__(self):
        self.database.close()

    def get_last_update(self):
        # check if ./last_update.txt exists
        if os.path.exists(last_update_file):
            with open(last_update_file, 'r') as f:
                last_update = int(f.read())
            # print('last_update:', last_update)
            return last_update
        else:
            # return 0 and create ./last_update.txt
            with open(last_update_file, 'w') as f:
                f.write('0')
            print('no last_update.txt, create one')
            return 0
        
    def update_last_update(self, last_update):
        with open(last_update_file, 'w') as f:
            f.write(str(last_update))
        print('last_update updated:', last_update)

    def check_and_update(self):
        self.last_update = self.get_last_update()
        # get items with timestamp > last_update
        #print('checking table:', self.table_name)
        response = self.table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('timestamp').gt(self.last_update)
        )
        items = response['Items']
        print(f'found {len(items)} new items')
        # update last_update
        if len(items) > 0:
            # sort items by timestamp
            items = sorted(items, key=lambda x: x['timestamp'])
            self.last_update = items[-1]['timestamp']
            self.update_last_update(self.last_update)
        # check if 'emic' in items ['original_message']
        download = False
        for item in items:
            msg = item['original_message'].lower()
            if '.emic' in msg and not download and 'update' in msg:
                crawler = CrawlerEMIC(debug=False)
                print('emic found in ', item['UUID'])
                crawler.login()
                try:
                    df_db = pd.read_sql('select * from emic', self.database)
                except:
                    df_db = pd.DataFrame(columns=['#','案件編號','發生時間/地點','災情類別','災情描述','權責單位','孤島狀態','通報來源'])
                old_cases_id = df_db['案件編號'].tolist()
                df = crawler.get_data(old_cases_id=old_cases_id)
                print('data downloaded and saved')
                df = df[~df['案件編號'].isin(df_db['案件編號'])]
                self.upload_data(df)
                print('data uploaded')
                # inform user with line message
                line_bot_api.reply_message(
                    item['reply_token'],
                    TextSendMessage(text=f'EMIC災情資料更新\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n新增{len(df)}筆資料', quick_reply=get_quick_reply())
                )
                self.save_data(df)
                download = True
            if '開設等級' in msg or 'status' in msg:
                print('開設等級 found in ', item['UUID'])
                crawler = CrawlerEMIC(debug=False)
                crawler.login()
                data = crawler.get_level()
                print('level:', data)
                # reply to line
                line_bot_api.reply_message(
                    item['reply_token'],
                    TextSendMessage(text=f'{data["name"]}\n總災情數:{data["tot"]}\n死亡人數:{data["dead"]}\n輕重傷人數:{data["hurt"]}\n失蹤人數:{data["missing"]}\n累計撤離人數:{data["leave"]}\n累計收容人數:{data["shelter"]}', quick_reply=get_quick_reply())
                )

                
    
    def save_data(self, df: pd.DataFrame):
        schema = {
            '#': 'int',
            '案件編號': 'PRIMARY KEY text',
            '發生時間/地點': 'text',
            '災情類別': 'text',
            '災情描述': 'text',
            '權責單位': 'text',
            '孤島狀態': 'text',
            '通報來源': 'text',
        }
        df.to_sql('emic', self.database, schema=schema, if_exists='append', index=False)
        print('data saved to sqlite database')

    def upload_data(self, df):
        # upload data not in sqlite database
        # try:
        #     df_db = pd.read_sql('select * from emic', self.database)
        # except:
        #     df_db = pd.DataFrame(columns=['#','案件編號','發生時間/地點','災情類別','災情描述','權責單位','孤島狀態','通報來源'])
        # df = df[~df['案件編號'].isin(df_db['案件編號'])]
        print(f'uploading {len(df)} new items')
        table = self.dynamodb.Table('data_emic')
        
        for _, row in df.iterrows():
            data = {
                'UUID': str(uuid4()),
                'timestamp': int(self.last_update + 1),
                'from': 'emic',
                'original_message': row['災情描述'],
                'case_id': row['案件編號'],
                'case_time_place': row['發生時間/地點'],
                'case_type': row['災情類別'],
            }
            table.put_item(Item=data)

def get_quick_reply():
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="幫助", text="rosa .help")),
        QuickReplyButton(action=MessageAction(label="開設等級", text="rosa .emic status")),
        QuickReplyButton(action=MessageAction(label="更新emic資訊", text="rosa .emic update")),
        QuickReplyButton(action=MessageAction(label="最近早期地震損失推估", text="rosa .teles")),
        QuickReplyButton(action=MessageAction(label="綁定通知", text="rosa .bindings")),
        ])
    return quick_reply

if __name__ == '__main__':
    print(datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'))
    checker = DynamoDBChecker()
    checker.check_and_update()