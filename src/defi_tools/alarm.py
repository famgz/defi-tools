import requests
import winsound
from famgz_utils import print, json_, countdown, clear_cmd_console
from pathlib import Path
from time import sleep

from .config import cfg
from .main import compare_values

PLAY_BEEP = 1
SEND_MESSAGE = 1
telegram_token = ''
telegram_chat_id = ''

headers = {
    'authority': 'api.thegraph.com',
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9,pt;q=0.8',
    'content-type': 'application/json',
    'origin': 'https://info.yewbow.org',
    'referer': 'https://info.yewbow.org/',
    'sec-ch-ua': '"Not_A Brand";v="99", "Brave";v="109", "Chromium";v="109"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
}


def get_pool(pool_ids: list):
    if not pool_ids:
        return

    pool_ids = str(pool_ids).replace("'", '"')
    json_data = {
        'operationName': 'pools',
        'variables': {},
        'query': 'query pools {\n  pools(\n    where: {id_in: %s}\n    orderBy: totalValueLockedUSD\n    orderDirection: desc\n    subgraphError: allow\n  ) {\n    id\n    feeTier\n    liquidity\n    sqrtPrice\n    tick\n    token0 {\n      id\n      symbol\n      name\n      decimals\n      derivedETH\n      __typename\n    }\n    token1 {\n      id\n      symbol\n      name\n      decimals\n      derivedETH\n      __typename\n    }\n    poolDayData(first: 95, orderBy: date, orderDirection: desc) {\n      txCount\n      volumeUSD\n      liquidity\n      feesUSD\n      volumeToken0\n      token1Price\n      __typename\n    }\n    token0Price\n    token1Price\n    volumeUSD\n    txCount\n    totalValueLockedToken0\n    totalValueLockedToken1\n    totalValueLockedUSD\n    feesUSD\n    __typename\n  }\n}\n' % pool_ids,
    }

    tries = 5
    base_wait = 1
    max_wait = 60
    for i in range(tries):
        try:
            r = requests.post('https://api.thegraph.com/subgraphs/name/ianlapham/uniswap-v3-polygon', headers=headers, json=json_data)
            rj = r.json()
            # json_('C://Users//GOOZ//Desktop//0x1aec019d1a0e3a024fef822a5728940c1d12dcbe.json', rj)
            return rj
        except Exception as e:
            print(f'[yellow]Error: {e} ({i+1})')
            wait = base_wait * (2**i)  # exponential waiting
            sleep(min(wait, max_wait))


def get_pool_tick(pool_id: str, rj: dict = None):
    rj = rj or get_pool([pool_id])
    [pool] = [pool for pool in rj['data']['pools'] if pool['id'] == pool_id]
    tick = float(pool['token1Price'])
    return tick


def get_telegram_tokens():
    global telegram_token
    global telegram_chat_id
    if telegram_token and telegram_chat_id:
        return
    path = Path(cfg.config_dir, 'tokens.txt')
    if not path.exists():
        print('[yellow]tokens.txt not found. Unable to send telegram message')
        return
    with open(Path(cfg.config_dir, 'tokens.txt')) as f:
        lines = [x.strip() for x in f.readlines() if x.strip()]
    if not lines:
        print('[yellow]tokens.txt is empty. Unable to send telegram message')
        return
    token = [x.split(' = ')[1].strip() for x in lines if x.startswith('telegram_token')]
    chat_id = [x.split(' = ')[1].strip() for x in lines if x.startswith('telegram_chat_id')]
    # TODO needs string validation
    if not token:
        print('[yellow]No telegram_token was found in tokens.txt. Unable to send telegram message')
        return
    if not chat_id:
        print('[yellow]No telegram_chat_id was found in tokens.txt. Unable to send telegram message')
        return
    telegram_token = token[0]
    telegram_chat_id = chat_id[0]
    print(
        f'telegram_token = {telegram_token}\n'
        f'telegram_chat_id = {telegram_chat_id}'
    )


def telegram_message(token='', chat_id='', msg='Hello World'):
    if not (token and chat_id):
        get_telegram_tokens()
    token = token or telegram_token
    chat_id = chat_id or telegram_chat_id
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
    print(url)
    r = requests.get(url)
    if not r.ok and 'json' in r.headers['Content-Type']:
        print(r.json())


def play_beep(n=1):
    '''TODO: to find a cross plataform sound solution'''
    n = min(n, 5)
    for i in range(n):
        # winsound.MessageBeep()
        winsound.PlaySound("C:\\Windows\\Media\\Ring03.wav", winsound.SND_FILENAME)
        if i==n:
            break
        # sleep(5)


def monitor_tick():

    def print_headers():
        print('POOLS ALARMS\n')
        for alarm in alarms:
            name     = alarm['name']
            min_tick = float(alarm['min_tick'])
            max_tick = float(alarm['max_tick'])
            print(f'{name} [white]pool [white]min_tick={min_tick} max_tick={max_tick}')
        print()

    alarms = [alarm | {'last_tick': None} for alarm in cfg.config_json['alarm'] if alarm['name'] and not alarm['ignore'] and cfg.validate_address(alarm['pool_id'])]

    if not alarms:
        print('Not enough data to process. Check config.json')
        return

    pool_ids = [alarm['pool_id'] for alarm in alarms]

    interval = 60 * 5  # minutes
    while True:
        clear_cmd_console()
        print_headers()

        # update data for pool_ids altogether
        rj = get_pool(pool_ids)

        for alarm in alarms:
            name     = alarm['name']
            pool_id  = alarm['pool_id']
            min_tick = float(alarm['min_tick'])
            max_tick = float(alarm['max_tick'])
            last_tick = alarm['last_tick']

            current_tick = get_pool_tick(pool_id, rj)
            alarm['last_tick'] = current_tick

            is_out_of_range = current_tick <= min_tick or current_tick >= max_tick
            out_msg = ' out of range ' if is_out_of_range else ''
            out_msg_f = f' [black on yellow]{out_msg}' if is_out_of_range else ''

            # first access or no changes
            if last_tick is None or current_tick == last_tick:
                # alarm['last_tick'] = current_tick
                print(f'{name} [white]pool current tick: [bright_white]{round(current_tick,6)}{out_msg_f}')
                continue

            # tick changed
            if current_tick != last_tick:
                diff = compare_values(current_tick, last_tick, n_digits=6, formatted=True)
                # alarm['last_tick'] = current_tick
                msg = f'{name} pool tick changed to {round(current_tick,6)} {diff}'
                print(f'[white]{msg}{out_msg_f}')
                if is_out_of_range:
                    if PLAY_BEEP:
                        play_beep()
                    if SEND_MESSAGE:
                        telegram_message(msg=msg + out_msg)

        countdown(interval)
