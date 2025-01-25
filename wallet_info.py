import os
import re
import sys
import time
import sqlite3
import requests
import datetime

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Environment variables
load_dotenv()
TG_TOKEN = os.getenv("TG_TOKEN")
BAL_LIMIT = int(os.getenv("BAL_LIMIT")) if os.getenv("BAL_LIMIT") else 100
RETRY_SPEED = int(os.getenv("RETRY_SPEED")) if os.getenv("RETRY_SPEED") else 1.1
IDLE_SPEED = int(os.getenv("IDLE_SPEED")) if os.getenv("IDLE_SPEED") else 720
URL_PREFIX = os.getenv("URL_PREFIX") if os.getenv("URL_PREFIX") else 'https://debank.com/profile/'
URL_SUFFIX = os.getenv("URL_SUFFIX") if os.getenv("URL_SUFFIX") else '/history?mode=analysis' # '?chain=bsc'

# Arguments
db_path = ''
chat_id = ''

# Append as a file
def log(text, filename = 'output.log'):
    if type(text) != 'str':
        text = str(text)
    file = open(filename, 'a', encoding='utf-8')
    file.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' ' + text + '\n')
    file.close()

# Save as a file
def save_file(text, filename = 'test.htm'):
    if type(text) != 'str':
        text = str(text)
    file = open(filename, 'w', encoding='utf-8')
    file.write(text)
    file.close()

# Send telegram message
def send_telegram_msg(message):
    log(f"[TG]\t{message}")

    global TG_TOKEN, chat_id
    if chat_id.isdigit(): # arg!
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
        requests.get(url).json()

# Function to create a database and a table, then insert a record
def add_record_to_db(addr, bal, age = None, pro = None, sum = None, last = None, table_name = "evm"):
    global db_path

    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Insert a new record
    cursor.execute(f'''
        INSERT INTO "{table_name}-history" (addr, bal, age, pro, sum, last) VALUES (?, ?, ?, ?, ?, ?)
    ''', (addr, bal, age, pro, sum, last))

    # Query to select a specific field value
    prev_val = 0
    cursor.execute(f'SELECT bal FROM "{table_name}" WHERE addr = "{addr}"')
    result = cursor.fetchone()
    if result:
        prev_val = result[0]

    # SQL command to update a record
    sql = f'UPDATE "{table_name}" SET bal=?, age=?, pro=?, sum=?, last=?, timestamp=CURRENT_TIMESTAMP WHERE addr=?'

    # Execute the update command
    cursor.execute(sql, (bal, age, pro, sum, last, addr))

    # Commit the changes and close the connection
    conn.commit()
    cursor.close()
    conn.close()

    return prev_val

# Chrome driver instance
def chrome_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--log-level=3')
    options.add_argument('--silent')
    options.add_argument('--disable-quic')
    return webdriver.Chrome(options=options)

# Get html content
count = 0 
maxco = 1000 # For avoid RAM overload
driver = None

def close_request_driver():
    global driver
    driver.close()
    driver.quit()
    driver = None

def get_html_with_request(url, xpath = None):
    global count, driver

    if count % maxco == 0 or driver == None:
        if driver != None:
            close_request_driver()
        driver = chrome_driver()
    count += 1

    driver.get(url)
    if xpath != None:
        WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, xpath)))
    else:
        time.sleep(1)
    return driver.page_source

# Parsing debank info
def parse_wallet_info(soup):
    # Find total balance
    el1 = soup.find('div', attrs={'class': 'HeaderInfo_totalAssetInner__HyrdC'})
    bal = re.sub(r'[\+\-].*$', '', el1.get_text().replace(',', '')) if el1 != None else None

    # Find active date
    el2 = soup.find('div', attrs={'class': 'db-user-tag is-age'})
    age = el2.get_text() if el2 != None else '-'

    # Find change info
    el3 = soup.find('span', attrs={'class': 'HeaderInfo_changePercent__0ze+J'})
    pro = el3.get_text() if el3 != None else '0%'

    # Top tokens in transactions
    sum = 0
    el4 = soup.find_all('div', attrs={'class': 'HistoryAnalysisView_topItemComponent__1pgjl'})
    for el in el4:
        spans = el.find_all('span')
        if len(spans) == 2:
            sum = sum + int(re.sub(r'[^\d]', '', spans[1].get_text().replace("$","").replace("K","000").replace("M","000000").replace("T","000000").replace(",","")))
    
    if sum > 9123456789123456789:
        sum = 9123456789123456789 # SQLite Int Max

    # Find last time
    el5 = soup.find('div', attrs={'class': 'History_sinceTime__yW4eC'})
    last = el5.get_text() if el5 != None else '-'

    return bal, age, pro, sum, last

def get_balance(wallet_address, errNotify):
    try:
        target_url = URL_PREFIX + '0x' + wallet_address
        waiting_obj = '//*[@class="HistoryAnalysisView_title__p6hjK"]'

        while True:
            html = get_html_with_request(URL_PREFIX + '0x' + wallet_address + URL_SUFFIX, waiting_obj)
            # save_file(html)
            if html.find("Request too fast") == -1:
                break

            # need to check if really have to break, in some case, shows correct value
            log(f'[ERROR3]\tRequest too fast, please try again later.')
            close_request_driver()
            time.sleep(IDLE_SPEED)

    except Exception as inst:
        log(f'[ERROR1]\t{wallet_address}\n{str(inst)}')
        if errNotify == True:
            send_telegram_msg(f"ERROR: Failed to get the page!\n{target_url}")
        return False

    try:
        soup = BeautifulSoup(html, 'html.parser')
        bal, age, pro, sum, last = parse_wallet_info(soup)
        log(f'[INFO]\t{wallet_address}:{bal}:{age}')

        if bal == "-" or bal.strip == "":
            if errNotify == True:
                send_telegram_msg(f"ERROR: Failed to get the balance!\n{target_url}")
            return False

        cur_val = int(re.sub(r'\.[\d]*$', '', bal.replace('$', ''))) # re.search(r'\d+', bal).group()
        prev_val = add_record_to_db(wallet_address, cur_val, age, float(pro.replace("%", "")), sum, last)

        if abs(cur_val-prev_val) > BAL_LIMIT or cur_val > BAL_LIMIT:
            send_telegram_msg(f"ALERT: {prev_val}->{cur_val}\n{target_url}")

        return True # No need to retry
    
    except Exception as inst:
        log(f'[ERROR2]\t{wallet_address}\n{str(inst)}')
        if errNotify == True:
            send_telegram_msg(f"ERROR: Failed to parse the page!\n{target_url}")
        return False

def get_todo_wallet_list(db_name, table_name = 'evm', filter = '>0'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    query = f'''
    SELECT addr FROM "{table_name}"
    WHERE che {filter}
    ORDER BY che DESC, timestamp ASC
    '''

    cursor.execute(query)
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results


# Check input
if len(sys.argv) < 2:
    print(f"ERROR: No input db argument!")
    sys.exit()

db_path = sys.argv[1]
chat_id = os.path.basename(db_path).replace(".db", "") # arg!
che_filter = sys.argv[2] if len(sys.argv) > 2 else '>0'

if not os.path.isfile(db_path):
    send_telegram_msg(f"ERROR: failed to find db file - '{db_path}'")
    sys.exit()

# Main loop
while True:
    send_telegram_msg("INFO: Begin loop!")
    list = get_todo_wallet_list(db_path, 'evm', che_filter)

    for row in list:
        for i in range(3): # times
            time.sleep(RETRY_SPEED + i * 5)
            if get_balance(row[0], i > 1) == True:
                break
    
    send_telegram_msg("INFO: End loop!")
    close_request_driver()
    time.sleep(IDLE_SPEED)