from copy import deepcopy
from famgz_utils import (
    clear_cmd_console,
    clear_last_console_line,
    countdown,
    f_time,
    input,
    json_,
    now,
    print,
    rule,
    sort_dict,
    timer,
    timestamp_to_date,
)
from os import symlink
from pathlib import Path
from time import sleep

from .config import cfg

headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive',
    'Origin': 'https://revert.finance',
    'Referer': 'https://revert.finance/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'Sec-GPC': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Brave";v="108"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

proxies = cfg.proxies
proxies = None
print('[bright_black]proxy: ', cfg.proxy) if proxies else ...

TIMEOUT = 300


def get_own_pools(wallet=None, network=None, pool_id=None, pool_dict=True, to_json=False, sort_by_date=True):

    output = {}

    # get single pool
    if pool_id:
        tries = 5
        base_wait = 1
        max_wait = 60
        for i in range(tries):
            try:
                # url = f'https://staging-api.revert.finance/v1/positions/{network}/uniswapv3/{pool_id}'
                url = f'https://api.revert.finance/v1/positions/{network}/uniswapv3/{pool_id}'
                r = cfg.session.get(url, headers=headers, timeout=TIMEOUT, proxies=proxies, verify=True)
                rj = r.json()
                data = rj['data']
                if not data.get('tokens'):
                    print(f'[yellow]Empty pool {network}/{pool_id} data ({i+1})\n', end='\r')
                    sleep(1)
                    continue
                output = {data['nft_id']: data} if pool_dict else data
                if i:
                    print()
                break
            except Exception as e:
                print(f'[yellow]Error: {e}')
                # print(rj)
                wait = base_wait * (2**i)
                sleep(min(wait, max_wait))  # exponential wait
        json_name = f'own_pools_{network}_{pool_id}.json'

    # get all pools
    elif wallet:
        # url = f'https://api.revert.finance/v1/positions/uniswapv3/account/{wallet}?active=true'  # <----- new api, fast, complete, all chains. change `active` param to get all/active pools
        # url = f'https://staging-api.revert.finance/v1/positions/{network}/uniswapv3/account/{wallet}'
        url = f'https://api.revert.finance/v1/positions/{network}/uniswapv3/account/{wallet}'
        r = cfg.session.get(url, headers=headers, timeout=TIMEOUT, proxies=proxies, verify=True)
        rj = r.json()
        if 'data' not in rj:
            print(f'[yellow]{rj}')
            return
        data = rj['data']
        output = {pool['nft_id']: pool for pool in data}
        if sort_by_date:
            output = dict(sorted(output.items(), key=lambda x: x[0]))
            # output = sorted(output, key=lambda x: x['first_mint_ts'])  # for lists
        json_name = f'own_pools_{wallet}_{network}.json'

    # save to json if data
    if to_json and output:
        path = Path(cfg.temp_dir, json_name)
        json_(path, output, backup=True, sort_keys=True, indent='\t')

    return output


def pool_pair(pool, formatted=False):
    tokens = [x['symbol'] for x in pool['tokens'].values()]
    # remove gas token
    if len(tokens) > 2:
        gas = 'WMATIC' if pool['network'] == 'polygon' else 'WETH'
        tokens.remove(gas)
    if formatted:
        tokens = '/'.join(tokens)
    return tokens


def pool_values(pool):
    # cash-flows references
    [mint]   = [x for x in pool['cash_flows'] if x['type'] == 'deposits' and x['timestamp'] == pool['first_mint_ts']]
    [cas]    = [x for x in pool['cash_flows'] if x['type'] == 'current-amount-state']
    deposits = [x for x in pool['cash_flows'] if x['type'] == 'deposits']
    pool_price = float(pool['pool_price'])
    has_priceless_token = not cas['prices']['token0']['usd'] or not cas['prices']['token1']['usd']
    # prices *fallback to alternative calculated values assuming at least one of tokens has valid price
    t0_price_usd_ini = float(mint['prices']['token0']['usd']) or float(mint['prices']['token1']['usd']) * mint['price']
    t1_price_usd_ini = float(mint['prices']['token1']['usd']) or float(mint['prices']['token0']['usd']) / mint['price']
    t0_price_usd_now = float(cas['prices']['token0']['usd']) or float(cas['prices']['token1']['usd']) * pool_price
    t1_price_usd_now = float(cas['prices']['token1']['usd']) or float(cas['prices']['token0']['usd']) / pool_price
    t0_price_t1_ini  = float(mint['prices']['token0']['token1']) or mint['price']                      # 1 t0 = n t1
    t1_price_t0_ini  = float(mint['prices']['token1']['token0']) or t0_price_usd_ini / mint['price']   # 1 t1 = n t0
    t0_price_t1_now  = float(cas['prices']['token0']['token1']) or pool_price                          # 1 t0 = n t1
    t1_price_t0_now  = float(cas['prices']['token1']['token0']) or t1_price_usd_now / t0_price_usd_now # 1 t1 = n t0
    # amounts
    # t0_ini         = float(pool['total_deposits0'])
    # t1_ini         = float(pool['total_deposits1'])
    t0_ini         = float(mint['deposited_token0'])
    t1_ini         = float(mint['deposited_token1'])
    t0_now         = float(pool['current_amount0'])
    t1_now         = float(pool['current_amount1'])
    t0_ini_usd_ini = t0_ini * t0_price_usd_ini
    t1_ini_usd_ini = t1_ini * t1_price_usd_ini
    t0_ini_usd_now = t0_ini * t0_price_usd_now
    t1_ini_usd_now = t1_ini * t1_price_usd_now
    t0_now_usd     = t0_now * t0_price_usd_now
    t1_now_usd     = t1_now * t1_price_usd_now
    invest_ini     = t0_ini_usd_ini + t1_ini_usd_ini  # mint exactly value
    invest_ini_now = t0_ini_usd_now + t1_ini_usd_now  # mint tokens with current value (to exclude fees)
    invest_now     = t0_now_usd + t1_now_usd if has_priceless_token else float(pool['underlying_value'])
    t0_percent_ini = t0_ini_usd_ini / invest_ini if invest_ini else 0
    t1_percent_ini = t1_ini_usd_ini / invest_ini if invest_ini else 0
    t0_percent = t0_now_usd / invest_now if invest_now else 0
    t1_percent = t1_now_usd / invest_now if invest_now else 0

    return {
        'has_priceless_token': has_priceless_token,
        'invest_ini': invest_ini,
        'invest_ini_now': invest_ini_now,
        'invest_now': invest_now,
        't0_price_usd_ini': t0_price_usd_ini,
        't1_price_usd_ini': t1_price_usd_ini,
        't0_price_usd_now': t0_price_usd_now,
        't1_price_usd_now': t1_price_usd_now,
        't0_price_t1_ini': t0_price_t1_ini,
        't1_price_t0_ini': t1_price_t0_ini,
        't0_price_t1_now': t0_price_t1_now,
        't1_price_t0_now': t1_price_t0_now,
        't0_ini': t0_ini,
        't1_ini': t1_ini,
        't0_ini_usd_ini': t0_ini_usd_ini,
        't1_ini_usd_ini': t1_ini_usd_ini,
        't0_now': t0_now,
        't1_now': t1_now,
        't0_now_usd': t0_now_usd,
        't1_now_usd': t1_now_usd,
        't0_percent_ini': t0_percent_ini,
        't1_percent_ini': t1_percent_ini,
        't0_percent': t0_percent,
        't1_percent': t1_percent,
    }


def pool_age(pool):
    # from timestamp
    if pool['age'] > 1:
        age = round(pool['age'], 1)
        return f'{age}d'
    diff = max(0, now() - pool['first_mint_ts'])
    mint = f_time(None, diff=diff, out='sep')
    day, hour = mint[0], mint[1]
    age = ' '.join( [x for x in (day, hour) if x] ) or '<1h'
    return age

    # from age string
    mint = float(pool['age'])
    day, hour = mint//1, mint%1
    day = f'{day}d ' if day else ''
    hour = f'{hour} h' if hour else ''
    return day + hour


def pool_mint_date(pool):
    mint = pool['first_mint_ts']
    date = timestamp_to_date(mint)
    return str(date)


def pool_range_scope(pool, formatted=False):
    price_lower = float(pool['price_lower'])
    price_upper = float(pool['price_upper'])
    mean = (price_upper + price_lower) / 2
    tick_lower = pool['tick_lower']
    tick_upper = pool['tick_upper']
    range_tick = tick_upper - tick_lower
    range_price = (price_upper / price_lower) - 1
    if formatted:
        range_price = format_to_percent(range_price, n_digits=None)
    return {
        'range_price': range_price,
        'range_tick': range_tick,
        'mean': mean
    }


def pool_range_bar(pool):

    def wrap_bar(bar):
        return bar_edge_l + (color_back + bar) + bar_edge_r

    t0, t1 = pool_pair(pool)
    price_current = float(pool['pool_price'])
    price_lower   = float(pool['price_lower'])
    price_upper   = float(pool['price_upper'])

    range_scope = pool_range_scope(pool)

    # █ ▌ ▐
    symbol_bar_empty     = '█'
    symbol_bar_full     = '█'
    symbol_tick     = '█'
    symbol_edge_r  = '▌'
    symbol_edge_l  = '▐'
    color_limit    = '[white]'
    color_back     = '[bright_black]'
    color_tick_in  = '[bright_green]'
    color_tick_out = '[bright_red]'

    bar_size = 50
    bar_edge_l = color_limit + symbol_edge_l
    bar_edge_r = color_limit + symbol_edge_r
    bar_tick_in = color_tick_in + symbol_tick
    bar_tick_out = color_tick_out + symbol_tick
    bar_empty = symbol_bar_empty * bar_size
    bar_full = symbol_bar_full * bar_size

    arrow_up   = '[bright_black]▲'
    arrow_down = '[bright_black]▼'

    tick_pos = 0

    if price_current <= price_lower:
        bar = bar_tick_out + wrap_bar(bar_empty)
        tick_pos = -1

    elif price_current >= price_upper:
        bar = ' ' + wrap_bar(bar_full) + bar_tick_out
        tick_pos = bar_size + 2

    else:
        step = (price_upper - price_lower) / bar_size
        vals = [price_lower + (step*i) for i in range(1, bar_size+1)]
        bar = []
        reached = False
        for i, val in enumerate(vals):
            # if val >= price_current:
            if price_current < val:
                if reached:
                    bar.append(symbol_bar_empty)
                else:
                    bar.append(bar_tick_in + color_back)
                    tick_pos = i+1
                    reached = True
                continue
            bar.append(symbol_bar_full)
        bar = ''.join(bar)
        bar = ' ' + wrap_bar(bar)

    header = f'[bright_black]{"100%":^9}{arrow_down}[white]{round(price_lower,4)}{round(price_upper,4):>{bar_size-len(str(round(price_lower,4)))}}{arrow_down}[bright_black]{"100%":^9}\n'
    bar = f'[bright_black]{t0:^8}{bar}[bright_black]{t1:^8}\n'
    footer = f'{"":{9+tick_pos}}{arrow_up}[white]{round(price_current,4)}'
    return header + bar + footer


def pool_fee_tier(pool):
    return float(pool['fee_tier']) / 10_000 / 100


def pool_gas(pool):
    gas_costs = [x for x in pool['cash_flows'] if x['type'] == 'gas-costs']
    gas     = sum( [abs(float(x['amount']))     for x in gas_costs] )
    gas_usd = sum( [abs(float(x['amount_usd'])) for x in gas_costs] )
    return {
        'gas': gas,
        'gas_usd': gas_usd,
    }


def pool_fees(pool, values):
    t0 = float(pool['total_fees0'])
    t1 = float(pool['total_fees1'])
    total = (t0 * values['t0_price_usd_now']) + (t1 * values['t1_price_usd_now']) if values['has_priceless_token'] else float(pool['fees_value'])
    return {
        'total': total,
        't0':    t0,
        't1':    t1,
    }


def pool_roi(pool, consider_mint_original_value=False):
    if consider_mint_original_value:
        roi = fees['total'] / values['invest_ini'] if values['invest_ini'] else 0
    # consider mint tokens with current value
    else:
        roi = fees['total'] / values['invest_ini_now'] if values['invest_ini_now'] else 0
    age = float(pool['age'])
    per_day = roi / age if age else roi
    per_week = per_day * 7
    per_month = per_day * 30
    per_year = per_day * 365
    return {
        'roi': roi,
        'per_day': per_day,
        'per_week': per_week,
        'per_month': per_month,
        'per_year': per_year,
    }


def parse_own_pools(include_exited=False, to_json=True):
    data = {}
    print('\n[white]Searching...', end='')
    for wallet in cfg.wallets:
        print(f'\n[white][bright_white]{cfg.wallets[wallet]:<10} [white]wallet on networks:', end=' ')
        for network in cfg.networks:
            pools = get_own_pools(network=network, wallet=wallet, to_json=False)
            pools = {pool_id: pool for pool_id, pool in pools.items() if (include_exited or not pool['exited']) and pool_id not in cfg.config_json['ignore'][network]}  # ignore exited pools as desired
            if not pools:
                print(f'[bright_black]{network}', end=' ')
                continue
            cfg.print_network(network, to_upper=False, end=' ')
            for pool_id, pool in pools.items():
                data.setdefault(wallet,{}).setdefault('networks',{}).setdefault(network,{}).setdefault('pools',{})[pool_id] = pool
                data.setdefault(wallet,{}).setdefault('total_invested',0)
                data.setdefault(wallet,{}).setdefault('networks',{}).setdefault(network,{}).setdefault('total_invested',0)
                data[wallet]['networks'][network]['total_invested'] += float(pool['underlying_value'])  # add up to wallet/network investment
                data[wallet]['total_invested'] += float(pool['underlying_value'])                       # add up to wallet investment
    # add track pools here ?
    if to_json and data:
        path = Path(cfg.temp_dir, 'own_pools_all.json')
        json_(path, data, backup=True, sort_keys=True, indent='\t')
    return data


def get_size_pools(data):
    ''' number of pools in all wallets/networks '''
    n = 0
    for wallet in data:
        networks = data[wallet]['networks']
        for network in networks.values():
            pools = network['pools']
            n += len(pools)
    return n


def get_network_pool_ids(data):
    ''' returns {networks: [pool_ids]} '''
    output = {
        'mainnet': [],
        'optimism': [],
        'polygon': [],
        'arbitrum': [],
    }
    for wallet in data:
        networks = data[wallet]['networks']
        for network, n in networks.items():
            pools = n['pools']
            for pool_id in pools:
                output[network].append(pool_id)
    return output


def monitor_open_pools(auto=None, include_exited=False):

    def filter_track_pools(data):
        ''' remove track pool_ids if in wallets '''
        track = cfg.config_json['track']
        pools_in_wallets = get_network_pool_ids(data)
        for network, pool_ids in pools_in_wallets.items():
            for pool_id in pool_ids:
                if pool_id in track[network]:
                    track[network].remove(pool_id)
        return track

    def add_track_pools(data):
        ''' in-place add unique track pool_ids to data '''
        print('\n[white]adding track pools...')
        track = cfg.config_json['track']
        pools_in_wallets = get_network_pool_ids(data)
        for network, pool_ids in track.items():
            for pool_id in pool_ids:
                if pool_id not in pools_in_wallets[network]:
                    print(network, pool_id)
                    pool = get_own_pools(network=network, pool_id=pool_id, pool_dict=False, to_json=False)
                    data.setdefault('track',{}).setdefault('networks',{}).setdefault(network,{}).setdefault('pools',{})[pool_id] = pool

    def first_stats(data):
        ref = data
        for wallet in ref:
            networks = ref[wallet]['networks']
            for network, n in networks.items():
                pools = n['pools']
                for pool_id, pool in pools.items():
                    values = pool_values(pool)
                    pool.update(first_fees=pool_fees(pool, values))  # record first fees
        return ref


    def print_stats(pool):

        def print_header():
            print()
            rule(f' {cfg.networks[network]["color"]}{pool_pair(pool, formatted=True)}[/] {format_to_percent(tier)} [bright_black]({pool_id}) ', style='bright_black')

        def print_range():
            in_range = pool['in_range']
            in_range = '' if in_range else '[black on yellow] out of range '
            range_scope = pool_range_scope(pool, formatted=True)
            mean = round(range_scope['mean'], 4)
            range_bar = pool_range_bar(pool)
            print(range_bar)
            print(
                f'[white]range_scope: [bright_white]{range_scope["range_price"]} | [white]{range_scope["range_tick"]} ticks | mean={mean} {in_range}'
            )

        def print_age():
            print(f'[white]age: [bright_white]{age} [bright_black]{pool_mint_date(pool)}')

        def print_tokens():
            total_ini = format_digits(values["invest_ini"])
            total_now = format_digits(values["invest_now"])
            total_now_w_fees = values["invest_now"] + fees['total']
            total_diff = compare_values(total_now, total_ini, formatted=True, colored=False)
            total_diff_w_fees = compare_values(total_now_w_fees, total_ini, formatted=True, colored=False)
            t0_ini = format_digits(values["t0_ini"])
            t1_ini = format_digits(values["t1_ini"])
            t0_now = format_digits(values["t0_now"])
            t1_now = format_digits(values["t1_now"])
            t0_now_usd = format_digits(values["t0_now_usd"])
            t1_now_usd = format_digits(values["t1_now_usd"])
            t0_price_usd_ini = format_digits(values["t0_price_usd_ini"], n_digits=4)
            t1_price_usd_ini = format_digits(values["t1_price_usd_ini"], n_digits=4)
            t0_price_usd_now = format_digits(values["t0_price_usd_now"], n_digits=4)
            t1_price_usd_now = format_digits(values["t1_price_usd_now"], n_digits=4)
            t0_price_t1_now = format_digits(values["t0_price_t1_now"], n_digits=4)
            t1_price_t0_now = format_digits(values["t1_price_t0_now"], n_digits=4)
            t0_percent_ini = format_to_percent(values["t0_percent_ini"], n_digits=None)
            t1_percent_ini = format_to_percent(values["t1_percent_ini"], n_digits=None)
            t0_percent = format_to_percent(values["t0_percent"], n_digits=None)
            t1_percent = format_to_percent(values["t1_percent"], n_digits=None)

            pad_t = max(len(t0), len(t1))
            pad_t_usd = max(len(t0_now_usd), len(t1_now_usd))
            pad_tt = max(len(t0_price_t1_now), len(t1_price_t0_now))
            pad_pct = max(len(t0_percent), len(t1_percent))
            pad_t_price_usd = max(len(t0_price_usd_now), len(t1_price_usd_now))

            mint_string = f'$[bright_white]{total_ini:>8} [white]({t0_ini} {t0} ${t0_price_usd_ini} ({t0_percent_ini}) | {t1_ini} {t1} ${t1_price_usd_ini} ({t1_percent_ini}))'

            print(
                f'[white]tokens:\n'
                f'  [white]{"MINT":<9}{mint_string}\n'
                f'  [white]{"CURRENT":<9}$[bright_white]{total_now:>8} [white]{total_diff} +fees: {format_digits(total_now_w_fees)} {total_diff_w_fees}\n'
                f'  [white]{t0:<10}[bright_white]{t0_now:>8} [white]({t0_percent:>{pad_pct}}) $ {t0_now_usd:>{pad_t_usd}} | 1 {t0:<{pad_t}} = {t0_price_t1_now:>{pad_tt}} {t1:<{pad_t}} = $ {t0_price_usd_now:>{pad_t_price_usd}}\n'
                f'  [white]{t1:<10}[bright_white]{t1_now:>8} [white]({t1_percent:>{pad_pct}}) $ {t1_now_usd:>{pad_t_usd}} | 1 {t1:<{pad_t}} = {t1_price_t0_now:>{pad_tt}} {t0:<{pad_t}} = $ {t1_price_usd_now:>{pad_t_price_usd}}'
            )

        def print_fees():
            n_dol = 2
            n_short = 2
            n_long = 4
            total = format_digits(fees['total'], n_digits=n_dol)
            total_diff = compare_values(fees['total'], first_fees['total'], n_digits=n_dol, formatted=True)
            t0_fee = format_digits(fees['t0'], n_digits=2)
            t1_fee = format_digits(fees['t1'], n_digits=2)
            t0_diff = compare_values(fees['t0'], first_fees['t0'], n_digits=4, formatted=True)
            t1_diff = compare_values(fees['t1'], first_fees['t1'], n_digits=4, formatted=True)
            print(
                f'[white]fees:\n'
                f'  [white]{"TOTAL":<9}$[bright_white]{total:>8} {total_diff}\n'
                f'  [white]{t0:<10}[bright_white]{t0_fee:>8} {t0_diff}\n'
                f'  [white]{t1:<10}[bright_white]{t1_fee:>8} {t1_diff}'
            )

        def print_roi():
            data = pool_roi(pool)
            roi = format_to_percent(data['roi'], symbol=False)
            per_day = format_to_percent(data['per_day'], symbol=False)
            per_month = format_to_percent(data['per_month'], symbol=False)
            per_year = format_to_percent(data['per_year'], symbol=False)
            print(
                f'[white]fees_roi:\n'
                f'  [white]{"ROI":<10}[bright_white]{roi:>8}[white] %\n'
                f'  [white]{"PER_DAY":<10}[bright_white]{per_day:>8}[white] %\n'
                f'  [white]{"PER_MONTH":<10}[bright_white]{per_month:>8}[white] %\n'
                f'  [white]{"PER_YEAR":<10}[bright_white]{per_year:>8}[white] %'
            )

        global t0, t1, tier, age, values, fees

        t0, t1 = pool_pair(pool)
        tier = pool_fee_tier(pool)
        age = pool_age(pool)
        values = pool_values(pool)
        gas = pool_gas(pool)
        fees = pool_fees(pool, values)

        print_header()
        print_range()
        print_age()
        print_tokens()
        print_fees()
        print_roi()

    if auto is None:
        ...
        # auto = input('Input any key to enable auto mode (refresh every n seconds)\n>')

    data = parse_own_pools(include_exited=include_exited)
    add_track_pools(data)  # request and add unique track pools to data
    if not data:
        print('[yellow]No open pools to monitor. Exiting...')
        return
    now_ts = now()
    first_access = True  # avoid redundant requests on first access
    ini = first_stats(data)  # save first data to later inquiries
    new = deepcopy(ini)

    n_pools = get_size_pools(new)

    t_ = 0
    min_interval = 60
    while True:
        if timer() - t_ < min_interval:
            print("[yellow]minimum time hasn't passed", end='')
        else:
            # request data
            t_ = timer()
            print('updating pools...')
            i = 1
            for wallet in new:
                new[wallet]['total_invested'] = 0
                networks = new[wallet]['networks']
                for network, n in networks.items():
                    networks[network]['total_invested'] = 0
                    pools = n['pools']
                    for pool_id, pool in pools.items():
                        # udpate pool
                        if not first_access:
                            pool = get_own_pools(network=network, pool_id=pool_id, pool_dict=False, to_json=False)
                        networks[network]['pools'][pool_id] = pool
                        # update total values
                        value = float(pool['underlying_value'])
                        new[wallet]['total_invested'] += value
                        networks[network]['total_invested'] += value
                        print(f'{i}/{n_pools}   ', end='\r')
                        i += 1
            first_access = False
            clear_cmd_console()

            # print data
            print('ACTIVE POOLS:')
            for wallet in new:
                print('\n')
                cfg.print_wallet(wallet)
                value = format_digits(new[wallet]['total_invested'])
                print(f'[white]$ {value}')
                networks = new[wallet]['networks']
                for network, n in networks.items():
                    print()
                    cfg.print_network(network)
                    value = format_digits(n['total_invested'])
                    print(f'[white]$ {value}')
                    pools = n['pools']
                    for pool_id, pool in pools.items():
                        first_fees = ini[wallet]['networks'][network]['pools'][pool_id]['first_fees']
                        print_stats(pool)
                rule(style='bright_white')

            print(f'[bright_black]elapsed: {f_time(now_ts)}')
        if auto:
            countdown(60, clear=True)
        else:
            input('\nEnter to refresh status\n>')


def format_digits(value, n_digits=2) -> str:
    ''' 2.1 -> 2.10 | 2 -> 2.00 '''
    n_digits = n_digits or 0
    value = float(value)
    return f'{value:.{n_digits}f}'
    a, *b = value.split('.')
    b = b[0] if b else 0
    b = b.ljust(n_digits, '0')
    return f'{a}.{b}'


def format_to_percent(number: float, n_digits=2, symbol=True):
    ''' 0.0123 -> 1.23% '''
    number = float(number)
    if not number:
        return '-'
    value = number * 100
    value = format_digits(value, n_digits=n_digits)
    symbol = '%' if symbol else ''
    return f'{value}{symbol}'


def reverse_from_percent(string: str):
    ''' 1.23% -> 0.0123 '''
    string = string.replace('%', '')
    value = float(string) / 100
    return value


def convert_text_to_digit(string: str):
    ''' 12.345m -> 12345000 '''
    multps = {
        'k': 1000,
        'm': 1000000,
        'b': 1000000000,
    }
    digits = "".join( [x for x in string if x.isdigit() or x == '.'] )
    suffix = "".join( [x for x in string if     x.isalpha()] )
    value = float(digits) * multps.get(suffix, 1)
    return value


def compare_values(now, ini, n_digits=2, formatted=False, colored=True):
    now, ini = float(now), float(ini)
    diff = now - ini
    # diff = round(diff, n_digits)
    if formatted:
        color = '[white]'
        plus = ''
        if diff < 0:
            color = '[bright_red]'
        if diff > 0:
            color = '[bright_green]'
            plus = '+'
        diff = format_digits(diff, n_digits=n_digits) if diff else 0
        color = color if colored else ''
        diff = f'{color}({plus}{diff})'
    return diff


def n_stables(pair):
    stables = [x.upper() for x in cfg.stablecoins]
    pair = pair.upper()
    t0, t1 = pair.split('/')
    return sum( [1 for x in (t0, t1) if x.strip() in stables] )


def get_top_pools():
    '''
    Temporary version
    For now, before running the code, you'll need to:
        Manually copy pools table data from https://info.uniswap.org/#/polygon/pools
        Paste all the text in /temp/top_pools.txt
    '''
    def export2excel():
        from pandas import DataFrame
        import pandas as pd
        data = [
            {
                'PAIR': x['pair'],
                'TIER': x['tier'],
                'TVL': x['_tvl'],
                'VOL_24H': x['_vol_24h'],
                'VOL_7D': x['_vol_7d'],
                '7D/TVL': x['ratio_7d_tvl'],
                '%1D': x['percent_1d'],
                '%1M': x['percent_1m'],
                '%1Y': x['percent_1y'],
                'N_STABLES': x['n_stables']
            }
            for x in pools
        ]
        df = DataFrame(data)

        # Create a Pandas Excel writer using XlsxWriter as the engine.
        path = Path(cfg.temp_dir, 'top_pools.xlsx')
        writer = pd.ExcelWriter(path, engine='xlsxwriter')

        # Convert the dataframe to an XlsxWriter Excel object.
        df.to_excel(writer, sheet_name='pools', index=False)

        # Get the xlsxwriter workbook and worksheet objects.
        workbook  = writer.book
        worksheet = writer.sheets['pools']

        # Get the dimensions of the dataframe.
        max_row, max_col = df.shape

        # Make the columns wider for clarity.
        worksheet.set_column(0,  max_col - 1, 15)
        worksheet.set_column(5,  5, 10)
        worksheet.set_column(max_col - 1,  max_col - 1, 10)

        # Set the autofilter
        worksheet.autofilter(0, 0, max_row, max_col - 1)

        # Add some cell formats.
        f_dolar = workbook.add_format({'num_format': '#,##0.00'})
        f_percent = workbook.add_format({'num_format': '0.00%'})

        # Set the format but not the column width.
        worksheet.set_column(1, 1, 10, f_percent)
        worksheet.set_column(2, 4, None, f_dolar)
        worksheet.set_column(6, 8, 10, f_percent)

        # Close the Pandas Excel writer and output the Excel file.
        writer.save()

        print('[bright_black]XLSX File succesfully written\n')

    def read_file():
        path = Path(cfg.temp_dir, 'top_pools.txt')
        with open(path) as f:
            file = f.read()
            file = file.replace('token logo', '')
            lines = [x.strip() for x in file.split('\n') if x.strip() and not x.strip().isdigit()]
            lines = [lines[i:i+5] for i in range(0, len(lines), 5)]
            assert not any( [x for x in lines if len(x) != 5] )
            return lines

    def parse_pools():
        pools = []
        for pair, tier, tvl, vol_24h, vol_7d in lines:
            _percent = reverse_from_percent(tier)
            _tvl      = convert_text_to_digit(tvl)
            _vol_24h  = convert_text_to_digit(vol_24h)  # biased, ignored
            _vol_7d   = convert_text_to_digit(vol_7d)
            ratio_7d_tvl = round(_vol_7d / _tvl, 2)
            mean_vol_24h  = _vol_7d / 7  # volume per day based on 7 days volume for accuracy matters
            yield_1d = mean_vol_24h * _percent  # daily yield distributed to participants
            percent_1d = yield_1d / _tvl
            percent_1m = percent_1d * 30
            percent_1y = percent_1m * 12
            stables = n_stables(pair)
            pools.append(
                {
                    'pair':      pair,
                    'tier':      tier,
                    'tvl':       tvl,
                    'vol_24h':   vol_24h,
                    'vol_7d':    vol_7d,
                    'yield_1d':  yield_1d,
                    '_percent':  _percent,
                    '_tvl':      _tvl,
                    '_vol_24h':  _vol_24h,
                    '_vol_7d':   _vol_7d,
                    'ratio_7d_tvl':   ratio_7d_tvl,
                    'percent_1d': percent_1d,
                    'percent_1m': percent_1m,
                    'percent_1y': percent_1y,
                    'n_stables': stables,
                }
            )
        return pools

    def print_results():
        pools_ = sorted(pools, key=lambda x: x['percent_1y'], reverse=True)
        pad1 = 14
        pad2 = 9
        print('[white]Percentages are mere estimates based on average weekly volume\n')
        print(f"[bright_yellow]{'PAIR':<{pad1}}{'TIER':<6}{'%1D':>{pad2}}{'%1M':>{pad2}}{'%1Y↓':>{pad2}}")
        for pool in pools_:
            pair = pool['pair']
            tier = pool['tier']
            percent_1d = format_to_percent(pool['percent_1d'])
            percent_1m = format_to_percent(pool['percent_1m'])
            percent_1y = format_to_percent(pool['percent_1y'])
            print(f"{pair:<{pad1}}[white]{tier:<6}{percent_1d:>{pad2}}{percent_1m:>{pad2}}{percent_1y:>{pad2}}")

    lines = read_file()

    pools = parse_pools()

    export2excel()

    print_results()


if __name__ == '__main__':
    get_own_pools()
