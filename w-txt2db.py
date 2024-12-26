# construct sqlite db from wallet list text file
#
# arg1: dir path of text files

import os
import re
import sys
import sqlite3


def read_file(filename):
    file = open(filename, 'r', encoding='utf-8')
    text = file.read()
    file.close()
    return text


def get_correct_wallet_addr_type(line):
    if line.strip() == "" or line.startswith('#'):
        return None, None

    m = re.search('[0-9a-fA-F]{40}', line)
    if m != None:
        return 'evm', m.group(0)

    n = re.search('T[0-9A-Za-z]{33}', line)
    if n != None:
        return 'tron', n.group(0)

    a = re.search('[1-9A-HJ-NP-Za-km-z]{32,44}', line)
    if a != None:
        return 'solana', a.group(0)

    return None, None


def add_record_to_db(db_name, table_name, addr):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            addr TEXT UNIQUE NOT NULL,
            bal INTEGER,
            age TEXT,
            pro REAL,
            sum INTEGER,
            last TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            che INTEGER DEFAULT 1,
            comment TEXT
        )
    ''')

    # Create table if it doesn't exist
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS "{table_name}-history" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            addr TEXT NOT NULL,
            bal INTEGER,
            age TEXT,
            pro REAL,
            sum INTEGER,
            last TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            comment TEXT
        )
    ''')

    # Insert a new record
    cursor.execute(f'''
        INSERT OR IGNORE INTO "{table_name}" (addr, timestamp) VALUES (?, ?)
    ''', (addr, None))

    # Commit the changes and close the connection
    cursor.close()
    conn.commit()
    conn.close()


if len(sys.argv) < 2:
    print(f"ERROR: No input dir argument!")
    sys.exit()

input_dir = sys.argv[1]
output_db = sys.argv[1] + ".db"

if not os.path.isdir(input_dir):
    print(f"ERROR: failed to find dir - '{input_dir}'")
    sys.exit()

for cur_file in os.listdir(input_dir):
    if not os.path.isfile(os.path.join(input_dir, cur_file)):
        continue

    wallet_list = read_file(os.path.join(input_dir, cur_file)).split('\n')
    for wallet_address in wallet_list:
        t, w = get_correct_wallet_addr_type(wallet_address)
        if t == None:
            continue

        print(f"{t}\t{w}")
        add_record_to_db(output_db, t, w)