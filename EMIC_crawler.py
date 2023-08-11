import time
from dotenv import load_dotenv
from selenium.webdriver import chrome
import os
import ddddocr
# import matplotlib.pyplot as plt
import datetime
import pandas as pd
import bs4

load_dotenv()
# add --disable-dev-shm-usage option
chrome_options = chrome.options.Options()
chrome_options.add_argument("start-maximized")
chrome_options.add_argument("disable-infobars")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument("--headless")


class CrawlerEMIC:

    # account_path = 'account.txt'
    captcha_path = os.path.join(os.path.dirname(__file__), 'captcha.png')

    def __init__(self, debug=False):
        self.debug = debug
        self.online = True
        # read the account and password from the file
        # with open(self.account_path, 'r') as f:
        #     self.account = f.readline().strip()
        #     self.password = f.readline().strip()
        self.account = os.getenv('EMIC_ACCOUNT')
        self.password = os.getenv('EMIC_PASSWORD')
        # check the account and password
        if self.account == '' or self.password == '':
            raise Exception('Please input the account and password in the file: ' + self.account_path)
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.driver = chrome.webdriver.WebDriver(options=chrome_options)
        self.driver.maximize_window()
        self.is_login = False

    def login(self):
        if self.driver:
            # open the login page
            try:
                self.driver.get('https://portal2.emic.gov.tw/SSO2_Develop/')
                captcha = self.driver.find_element('xpath', '//*[@id="captcha"]')
                # save the captcha image
                captcha.screenshot(self.captcha_path)

                # input the account and password
                tb_account = self.driver.find_element('xpath', '//*[@id="inputAccount"]')
                tb_account.send_keys(self.account)

                tb_password = self.driver.find_element('xpath', '//*[@id="inputPassword"]')
                tb_password.send_keys(self.password)

                # use ddddocr to recognize the captcha image
                ocr = ddddocr.DdddOcr(show_ad=False)
                with open(self.captcha_path, 'rb') as f:
                    img_bytes = f.read()
                res = ocr.classification(img_bytes)
                # print log
                print('Captcha recognized: ' + res)

                # input the recognized text
                tb_captcha = self.driver.find_element('xpath', '//*[@id="inputCaptcha"]')
                tb_captcha.send_keys(res)

                # click the login button
                btn_login = self.driver.find_element('xpath', '//*[@id="LoginForm"]/div[5]/div[1]/button')
                # open the captcha image
                # img = plt.imread(self.captcha_path)
                # # add the recognized text to the image
                # plt.text(0, 0, res, fontsize=20, color='red')
                # plt.imshow(img)
                # plt.show()
                btn_login.click()

                # if  not self.debug:
                #     btn_login.click()

                # if self.debug:
                #     # open the captcha image
                #     img = plt.imread(self.captcha_path)
                #     # add the recognized text to the image
                #     plt.text(0, 0, res, fontsize=20, color='red')
                #     plt.imshow(img)
                #     plt.show()

                # check the login status
                if self.driver.current_url.startswith('https://portal2.emic.gov.tw/SSO2_Develop/SSO'):
                    print('Login success')
                    self.is_login = True
                else:
                    print('Login failed')
                    self.is_login = False
                    # save error page
                    current_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                    self.driver.save_screenshot('error_' + current_time + '.png')
                    # try again
                    self.login()
            except Exception as e:
                print(e)
                # save error page
                current_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                self.driver.save_screenshot('error_' + current_time + '.png')

    def handel_switch(self, n_center=0, project=0):
        """
        切換應變中心-專案
        """
        try:
            try:
                switch = self.driver.find_element('xpath', '/html/body/div[3]/div/div[1]/h2')
            except:
                loading = self.driver.find_element('xpath', '/html/body/div[1]/main/div[4]/div/div[9]/div/div/div/div[2]/div/div[2]/div[2]/div[2]/div')
                while loading.is_displayed():
                    pass
                return
            if switch.text == '切換應變中心-專案':
                centers = self.driver.find_element('xpath', f'/html/body/div[3]/div/div[2]/div/div[1]/div')
                # default click the first <a> in centers, if n_center != 0, click the n_center th <a>
                centers.find_elements('xpath', './a')[n_center].click()
                projects = self.driver.find_element('xpath', f'/html/body/div[3]/div/div[2]/div/div[2]/div')
                # default click the first <a> in projects, if project != 0, click the project th <a>
                projects.find_elements('xpath', './a')[project].click()

                confirm_switch = self.driver.find_element('xpath', '/html/body/div[3]/div/div[3]/a')
                confirm_switch.click()
        except Exception as e:
            print(e)
            # save error page
            current_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            self.driver.save_screenshot('error_' + current_time + '.png')

    def get_level(self):
        if not self.is_login:
            raise Exception('Please login first')
        # go into EMIC page
        try:
            self.diver.find_element('xpath', '/html/body/div[4]/main/div[4]/div/section[1]/div/div[1]/div/div/a/img').click()
        except:
            link = "http://portal2.emic.gov.tw/EMP2_Develop/"
            # open the link in a new tab
            self.driver.execute_script("window.open('" + link + "');")
            # print('warning: element not found, use link')
        # switch to the new tab
        self.driver.switch_to.window(self.driver.window_handles[-1])

        self.handel_switch()

        while(self.driver.find_element('xpath', '//*[@id="tot"]').text == ''):
            time.sleep(0.5)
        name = self.driver.find_element('xpath', '/html/body/header[1]/ul/li[1]/span/div/span[2]').text
        level = self.driver.find_element('xpath', '/html/body/header[1]/ul/li[1]/span/div/span[2]/span').text
        tot = self.driver.find_element('xpath', '//*[@id="tot"]').text
        dead = self.driver.find_element('xpath', '//*[@id="deadPeople"]').text
        hurt = self.driver.find_element('xpath', '//*[@id="hurtPeople"]').text
        missing = self.driver.find_element('xpath', '//*[@id="missingPeople"]').text
        leave = self.driver.find_element('xpath', '//*[@id="leavePeople"]').text
        shelter = self.driver.find_element('xpath', '//*[@id="shelterPeople"]').text

        data = {
            'name': name,
            'level': level,
            'tot': tot,
            'dead': dead,
            'hurt': hurt,
            'missing': missing,
            'leave': leave,
            'shelter': shelter
        }
        return data

    def get_data(self, old_cases_id=[]):
        try:
            if not self.is_login:
                raise Exception('Please login first')
            # go into EMIC page
            try:
                self.diver.find_element('xpath', '/html/body/div[4]/main/div[4]/div/section[1]/div/div[1]/div/div/a/img').click()
            except:
                link = "http://portal2.emic.gov.tw/EMP2_Develop/"
                # open the link in a new tab
                self.driver.execute_script("window.open('" + link + "');")
                # print('warning: element not found, use link')
            # switch to the new tab
            self.driver.switch_to.window(self.driver.window_handles[-1])
            # 災情管理 page
            try:
                self.driver.find_element('xpath', '/html/body/div[1]/div/nav/ul/li[4]/div/ul/li[2]/ul/li[2]').click()
            except:
                self.driver.get('http://portal2.emic.gov.tw/DIM2_Develop/DIM2010101/Index')
                # print('warning: element not found, use link')
            self.handel_switch()
            time.sleep(1)
            # redirect to 災情管理 page
            self.driver.get('http://portal2.emic.gov.tw/DIM2_Develop/DIM2010101/Index')
            time.sleep(1)
            try:
                loading_elemnt = self.driver.find_element('xpath', '/html/body/div[1]/main/div[4]/div/div[9]/div/div/div/div[2]/div/div[2]/div[2]/div[2]/div')
                while loading_elemnt.is_displayed():
                    pass
            except:
                loading_elemnt = None
            # wait for the loading element disappear

            # number of rows
            # wait until n_rows is not empty
            while True:
                n_rows = self.driver.find_elements('xpath', '/html/body/div[1]/main/div[4]/div/div[9]/div/div/div/div[2]/div/div[2]/div[2]/div[4]/div[1]/span/div/div[2]')
                if n_rows[0].text != '':
                    break
            n_rows = int(n_rows[0].text[2:-2])
            print('共有' + str(n_rows) + '筆資料')
            df = pd.DataFrame(columns=['#','案件編號','發生時間/地點','災情類別','災情描述','權責單位','孤島狀態','通報來源'])
            row_count = 0
            while row_count < n_rows:
            ## TODO: compare the old_cases_id to stop the loop
                # get the table
                table = self.driver.find_element('xpath', '/html/body/div[1]/main/div[4]/div/div[9]/div/div/div/div[2]/div/div[2]/div[2]/div[2]/table')
                # get the table content
                table_html = table.get_attribute('outerHTML')
                # save the table content
                with open(os.path.join(os.path.dirname(__file__), f'html/table_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}_{row_count}.html'), 'w', encoding='utf-8') as f:
                    f.write(table_html)
                # convert the table content to dataframe
                df = pd.concat([df, self.html_to_df(table_html)], ignore_index=True)
                row_count = len(df)
                ##
                if df['案件編號'].isin(old_cases_id).any():
                    break
                old_cases_id.append(df['案件編號'].tolist())
                # next page 
                # item in list:/html/body/div[1]/main/div[4]/div/div[9]/div/div/div/div[2]/div/div[2]/div[2]/div[4]/div[2]/ul
                ul = self.driver.find_element('xpath', '/html/body/div[1]/main/div[4]/div/div[9]/div/div/div/div[2]/div/div[2]/div[2]/div[4]/div[2]/ul')
                # class = page-item page-next
                next = ul.find_element('xpath', './li[@class="page-item page-next"]')
                next.click()
                time.sleep(2)
                # wait for the loading element disappear
                if not loading_elemnt:
                    try:
                        loading_elemnt = self.driver.find_element('xpath', '/html/body/div[1]/main/div[4]/div/div[9]/div/div/div/div[2]/div/div[2]/div[2]/div[2]/div')
                        while loading_elemnt.is_displayed():
                            pass
                    except:
                        loading_elemnt = None

            # save the dataframe
            df.to_csv(os.path.join(os.path.dirname(__file__), f'csv/table_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.csv'), index=False)
            # print(df)
            print('資料下載完成', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        except Exception as e:
            print(e)
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.driver.save_screenshot(os.path.join(os.path.dirname(__file__), f'screenshot/{current_time}.png'))
        return df

    def html_to_df(self, html):
        soup = bs4.BeautifulSoup(html, 'html.parser')
        columns = []
        for th in soup.find_all('th'):
            columns.append(th.text.strip())
        df = pd.DataFrame(columns=columns)
        for tr in soup.find_all('tr'):
            row = []
            for td in tr.find_all('td'):
                row.append(td.text.strip())
            if len(row) > 0:
                df.loc[len(df)] = row
        return df
    
if __name__ == '__main__':
    crawler = CrawlerEMIC(debug=False)
    crawler.login()
    crawler.get_data()
    input('press any key to exit')