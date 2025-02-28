# pip install web3

from web3 import Web3
from eth_account import Account

oneeyOrsee = [
"f95845daa26bffa28dacf40167aa70d987d6e8a41cd05c7ff0909f6dda9eef77",
"diary benefit wave borrow erode cement train more arm jewel acquire duck"
]

def printa(s):
    a, b = -4, -2
    s_list = list(s)
    s_list[a], s_list[b] = s_list[b], s_list[a]    
    return ''.join(s_list)

def printb(s):
    a, b = -4, -2
    s_list = s.split()
    s_list[a], s_list[b] = s_list[b], s_list[a]    
    return ' '.join(s_list)

def s2a(see, count=20):
    w3 = Web3();
    w3.eth.account.enable_unaudited_hdwallet_features();
    for i in range(count):
        acc = w3.eth.account.from_mnemonic(see, account_path=f"m/44'/60'/0'/0/{i}")
        if i == 0:
            print(acc.address, "\t", printb(see));
        else:
            print(acc.address, "\t", f'#{i + 1}');


for one in oneeyOrsee:
    try:
        if one.find(" ") == -1:
            print(Account.from_key(one).address, "\t", printa(one));
        else:
            s2a(one);
    except:
        pass;