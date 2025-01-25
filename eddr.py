# pip install web3

from web3 import Web3
from eth_account import Account

oneeyOrseed = [
"f95845daa26bffa28dacf40167aa70d987d6e8a41cd05c7ff0909f6dda9eef77",
"diary benefit wave borrow erode cement train more arm jewel acquire duck"
]


def seed2addrs(seed, count=20):
    w3 = Web3();
    w3.eth.account.enable_unaudited_hdwallet_features();
    for i in range(count):
        acc = w3.eth.account.from_mnemonic(seed, account_path=f"m/44'/60'/0'/0/{i}")
        if i == 0:
            print(acc.address, "\t", seed);
        else:
            print(acc.address, "\t", f'### {i + 1}');


for one in oneeyOrseed:
    try:
        if one.find(" ") == -1:
            print(Account.from_key(one).address, "\t", one);
        else:
            seed2addrs(one);
    except:
        pass;