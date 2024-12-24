import os
import re
import sys
import time
import json
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
BAL_LIMIT = int(os.getenv("BAL_LIMIT"))
SOL_PRICE = float(os.getenv("SOL_PRICE"))
TG_TOKEN = os.getenv("TG_TOKEN")

# Some urls
base_url = 'https://debank.com/profile/'
tron_url = 'https://tronscan.org/#/address/'
sola_url = 'https://solscan.io/account/'

chat_id = "" # argument

# Send telegram message
def send_telegram_msg(message):
    global TG_TOKEN, chat_id
    if chat_id.isdigit():
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
        requests.get(url).json() # this sends the message
    else:
        print(message)

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

    if count % 10 == 0:
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
    bal = re.sub(r'[\+\-].*$', '', el1.get_text().replace(',', '')) if el1 != None else '-'

    # Find active date
    el2 = soup.find('div', attrs={'class': 'db-user-tag is-age'})
    age = el2.get_text() if el2 != None else '-'
    
    return bal, age

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
                        send_telegram_msg(f"{sola_url}{line}\nPrice: ${int(bal*SOL_PRICE)}\nBal: {bal} SOL")

                return True

        # Scraping
        if tron_flag == True:
            target_url = tron_url + wallet_address
            waiting_obj = '//*[@class="address-asset-num"]'
        else:
            target_url = base_url + '0x' + wallet_address
            waiting_obj = '//*[@class="UpdateButton_updateTimeNumber__9wXmw"]'
            
        html = get_html_with_request(target_url, waiting_obj)

    except Exception as inst:
        append_file(f'{wallet_address}:ERROR1:{target_url}\n', outputFile)
        if errNotify == True:
            send_telegram_msg(f"{target_url}\nFailed to get the page!\n{str(inst)}")
        return False

    try:
        soup = BeautifulSoup(html, 'html.parser')
        if tron_flag == True:
            bal, age = parse_tron_info(soup)
        else:
            bal, age = parse_wallet_info(soup)
        append_file(f'{wallet_address}:{bal}:{age}\n', outputFile)

        if bal == "-" or bal.strip == "":
            if errNotify == True:
                send_telegram_msg(f"{target_url}\nFailed to get the balance!\nBal: {bal}\nAge: {age}")
            return False

        if int(re.search(r'\d+', bal).group()) > BAL_LIMIT:
            send_telegram_msg(f"{target_url}\nBal: {bal}\nAge: {age}")
        return True
    
    except Exception as inst:
        append_file(f'{wallet_address}:ERROR2:{target_url}\n', outputFile)
        if errNotify == True:
            send_telegram_msg(f"{target_url}\nFailed to parse the page!\n{str(inst)}")
        return False

# Check input dir.
if len(sys.argv) > 1:
    input_dir = sys.argv[1]
    chat_id = os.path.basename(sys.argv[1])
else:
    print("No input dir argument!")
    exit()

if not os.path.isdir(input_dir):
    send_telegram_msg("Not exist:", input_dir)
    exit()

# Create output dir.
output_dir = input_dir.replace("input", "output")
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Main loop
while True:
    send_telegram_msg("Begin loop!")

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
    
    send_telegram_msg("End loop!")
    time.sleep(60)