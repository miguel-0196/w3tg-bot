import os
import re
import sys
import time
import json
import sqlite3
import datetime
import requests

from solana.rpc.api import Client
from solders.pubkey import Pubkey

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Environment variables
load_dotenv()
BAL_LIMIT = int(os.getenv("BAL_LIMIT")) if os.getenv("BAL_LIMIT") else 100
SOL_PRICE = float(os.getenv("SOL_PRICE")) if os.getenv("SOL_PRICE") else 199.21
TG_TOKEN = os.getenv("TG_TOKEN")

# Some urls
base_url = 'https://debank.com/profile/'
tron_url = 'https://tronscan.org/#/address/'
sola_url = 'https://solscan.io/account/'

chat_id = "main"

# Send telegram message
def send_telegram_msg(message):
    global TG_TOKEN, chat_id
    if chat_id.isdigit(): # arg!
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
        requests.get(url).json() # this sends the message
    else:
        print("TG>>", message)

# Save as a file
def save_file(text, filename = 'test.htm'):
    if type(text) != 'str':
        text = str(text)
    file = open(filename, 'w', encoding='utf-8')
    file.write(text)
    file.close()

# Append as a file
def append_file(text, filename = 'output.txt'):
    if type(text) != 'str':
        text = str(text)
    file = open(filename, 'a', encoding='utf-8')
    file.write(text)
    file.close()

# Read file
def read_file(filename = 'test.htm'):
    file = open(filename, 'r', encoding='utf-8')
    text = file.read()
    file.close()
    return text

# Save as json
def save_json_file(json_value, file_path):
    with open(file_path, 'a') as file:
        # Write the JSON data to the file
        json.dump(json_value, file)

def is_valid_solana_address(address):
    # Regular expression to validate Solana wallet address
    return re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) is not None

def get_sol_balance(address):
    # Connect to the Solana devnet
    client = Client("https://api.mainnet-beta.solana.com")

    # Fetch and display the wallet's balance
    balance_response = client.get_balance(Pubkey.from_string(address))
    balance = balance_response.value if hasattr(balance_response, 'value') else None

    if balance is not None:
        sol_balance = balance / 1_000_000_000
        return sol_balance
    else:
        return 0

# Function to create a database and a table, then insert a record
def add_record_to_db(addr, bal, age = None, pro = None, sum = None, last = None):
    global chat_id
    db_name = 'output.db'
    table_name = chat_id

    # Connect to the SQLite database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            addr TEXT NOT NULL,
            bal INTEGER,
            age TEXT,
            pro REAL,
            sum INTEGER,
            last TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            che INTEGER DEFAULT 0,
            comment TEXT
        )
    ''')

    # Insert a new record
    cursor.execute(f'''
        INSERT INTO "{table_name}" (addr, bal, age, pro, sum, last) VALUES (?, ?, ?, ?, ?, ?)
    ''', (addr, bal, age, pro, sum, last))

    # Commit the changes and close the connection
    cursor.close()
    conn.commit()
    conn.close()

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
count = 0 # For avoid RAM overload
driver = None
def get_html_with_request(url, xpath = None):
    global count, driver

    if count % 20 == 0:
        driver = chrome_driver()
    count += 1

    driver.get(url)
    if xpath != None:
        WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, xpath)))
    else:
        time.sleep(1)
    return driver.page_source

def close_request_driver():
    global count, driver
    count = 0
    driver.close()
    driver.quit()

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
            sum = sum + int(spans[1].get_text().replace("$","").replace("K","000").replace("M","000000"))

    # Find last time
    el5 = soup.find('div', attrs={'class': 'History_sinceTime__yW4eC'})
    last = el5.get_text() if el5 != None else '-'

    return bal, age, pro, sum, last

# Parsing tron info
def parse_tron_info(soup):
    # Find total balance
    el1 = soup.find('span', attrs={'class': 'address-asset-num'})
    bal = re.sub(r'[\+\-].*$', '', el1.get_text().replace(',', '')) if el1 != None else '-'

    # Find active date
    el2 = soup.find('span', attrs={'class': 'activity-num'})
    age = re.sub(r'[\s\:].*$', '', el2.get_text()) if el2 != None else '-'
    
    return bal, age

# Get balance
def get_balance(line, errNotify, outputFile):
    try:
        if line.strip() == "" or line.startswith('#'):
            return True # No need to retry

        # Find wallet addr
        wallet_address = f"@{line}" # for exception
        tron_flag = False
        m = re.search('[0-9a-fA-F]{40}', line)
        if m != None:
            wallet_address = m.group(0)
        else:
            n = re.search('^T[0-9A-Za-z]{33}', line)
            if n != None:
                wallet_address = n.group(0)
                tron_flag = True
            else:
                # solana case
                if is_valid_solana_address(line):
                    bal = get_sol_balance(line)
                    append_file(f'{line}:${int(bal*SOL_PRICE)}:{bal}SOL\n', outputFile)

                    if bal > 0:
                        send_telegram_msg(f"ALERT: {bal} SOL\nURL: {sola_url}{line}")

                return True

        # Scraping
        if tron_flag == True:
            target_url = tron_url + wallet_address
            waiting_obj = '//*[@class="address-asset-num"]'
        else:
            target_url = base_url + '0x' + wallet_address + '/history?mode=analysis'
            waiting_obj = '//*[@class="HistoryAnalysisView_title__p6hjK"]'
            
        html = get_html_with_request(target_url, waiting_obj)

    except Exception as inst:
        append_file(f'{wallet_address}:ERROR1:{target_url}\n', outputFile)
        if errNotify == True:
            send_telegram_msg(f"ERROR: Failed to get the page!\n{str(inst)}\nURL: {target_url}")
        return False

    try:
        bal, age, pro, sum, last = None, None, None, None, None

        soup = BeautifulSoup(html, 'html.parser')
        if tron_flag == True:
            bal, age = parse_tron_info(soup)
        else:
            bal, age, pro, sum, last = parse_wallet_info(soup)
        append_file(f'{wallet_address}:{bal}:{age}\n', outputFile)

        if bal == "-" or bal.strip == "":
            if errNotify == True:
                send_telegram_msg(f"ERROR: Failed to get the balance!\nURL: {target_url}")
            return False

        if int(re.search(r'\d+', bal).group()) > BAL_LIMIT:
            send_telegram_msg(f"ALERT: {bal}\nURL: {target_url}")

        if pro != None:
            add_record_to_db(wallet_address, int(re.sub(r'\.[\d]*$', '', bal.replace('$', ''))), age, float(pro.replace("%", "")), sum, last)
        else:
            add_record_to_db(wallet_address, int(re.sub(r'\.[\d]*$', '', bal.replace('$', ''))), age, None, sum, last)
        return True
    
    except Exception as inst:
        append_file(f'{wallet_address}:ERROR2:{target_url}\n', outputFile)
        if errNotify == True:
            send_telegram_msg(f"ERROR: Failed to parse the page!\n{str(inst)}\nURL: {target_url}")
        return False

# Check input dir.
if len(sys.argv) > 1:
    input_dir = sys.argv[1]
    chat_id = os.path.basename(sys.argv[1]) # arg!
else:
    print(f"ERROR: No input dir argument!")
    exit()

if not os.path.isdir(input_dir):
    send_telegram_msg(f"ERROR: failed to find '{input_dir}'")
    exit()

# Create output dir.
output_dir = input_dir.replace("input", "output") # arg!
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Main loop
while True:
    send_telegram_msg("INFO: Begin loop!")

    for cur_file in os.listdir(input_dir):
        if not os.path.isfile(os.path.join(input_dir, cur_file)):
            continue

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_file = os.path.join(output_dir, f"{cur_file.replace('.txt', '')}-{timestamp}.out")

        wallet_list = read_file(os.path.join(input_dir, cur_file)).split('\n')
        for wallet_address in wallet_list:
            for i in range(3):
                time.sleep(3)
                if get_balance(wallet_address, i > 1, output_file) == True:
                    break
    
    send_telegram_msg("INFO: End loop!")
    close_request_driver()
    time.sleep(60)