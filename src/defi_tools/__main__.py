import sys
from famgz_utils import print, input
from pathlib import Path

from .config import cfg

opts = {
    'top_pools' : ('', 'parse all available pools from manually pasted text in pools.txt'),
    'own_pools' : ('', 'parse own pools'),
    'monitor'   : ('', 'monitor open own pools'),
    'alarm'     : ('', 'monitor pool tick changes and alarm'),
}


def make_bats():
    if not cfg.bats_dir.is_dir():
        Path.mkdir(cfg.bats_dir)
    for opt in opts:
        name = f'{opt}.bat'
        bat_path = Path(cfg.bats_dir, name)
        if bat_path.exists():
            continue
        string = f'python -m defi {opt}\npause\n'
        with open(bat_path, 'w') as f:
            f.write(string)


def message():
    print('[yellow]ERROR, you must parse a mode:\n')
    [print(f'[bright_green]{mode + "[green]" + param + "[bright_black]":.<46}[white]{desc}') for mode, (param, desc) in opts.items()]


make_bats()

if __name__ == '__main__':

    if len(sys.argv) != 2:
        message()
        sys.exit()

    args = sys.argv[1].strip()
    opt, *arg = args.split('=')
    arg = arg[0] if arg else None

    if opt not in opts:
        message()
        sys.exit()

    if opt == 'top_pools':
        from .main import get_top_pools
        get_top_pools()

    elif opt == 'own_pools':
        from .main import parse_own_pools
        parse_own_pools(include_exited=True, to_json=True)

    elif opt == 'monitor':
        from .main import monitor_open_pools
        monitor_open_pools(include_exited=False)

    elif opt == 'alarm':
        from .alarm import monitor_tick
        monitor_tick()
