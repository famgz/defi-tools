import requests
from famgz_utils import print, input, json_, now
from pathlib import Path
from web3 import Web3


class Config:

    def __init__(self):
        self._core_paths()
        self._first_run_check()
        self._core_json()
        self._update_wallets()
        self._load_proxies()
        self.session = requests.Session()
        self.networks = {  # TODO: implement other uniswapv3 networks
            # 'mainnet': {'color': '[bright_cyan]'},
            # 'optimism': {'color': '[bright_red]'},
            'polygon': {'color': '[bright_magenta]'},
            # 'arbitrum': {'color': '[bright_blue]'},
        }
        self.stablecoins = [
            'BEAN', 'BUSD', 'cUSD', 'DAI', 'DOLA', 'FEI', 'FLEXUSD', 'FRAX',
            'GUSD', 'HUSD', 'LUSD', 'MIM', 'miMATIC', 'MUSD', 'OUSD', 'RSV',
            'SUSD', 'TUSD', 'USDC', 'USDD', 'USDN', 'USDP', 'USDT', 'USDX',
            'USTC', 'VAI', 'fxUSD', 'USDs', 'cEUR'
        ]

    '''
    FOLDER AND FILE PATHS
    '''

    def _core_paths(self):
        ''' Load all paths '''
        # folders paths
        self.source_dir = Path(__file__).resolve().parent
        self.config_dir = Path(self.source_dir, 'config')
        self.data_dir = Path(self.source_dir, 'data')
        self.temp_dir = Path(self.source_dir, 'temp')
        self.bats_dir = Path(self.source_dir, 'bats')
        self._folders = [
            self.config_dir,
            self.data_dir,
            self.temp_dir,
            self.bats_dir,
        ]
        # json files paths
        self._path_config_json = Path(self.config_dir, 'config.json')
        self._path_invest_json = Path(self.config_dir, 'invest.json')

    def _core_json(self):
        ''' Load all json files '''
        self.config_json = json_(self._path_config_json)
        self.invest_json = json_(self._path_invest_json)

    def update_json(self, file):
        files = {
            'config': {'path': self._path_config_json, 'data': self.config_json},
            'invest': {'path': self._path_invest_json, 'data': self.invest_json},
        }
        path = files[file]['path']
        data = files[file]['data']
        json_(path, data, backup=True, indent='\t', ensure_ascii=False)

    def _first_run_check(self):
        self._check_folders()
        self._check_files()

    def _check_folders(self):
        for folder in self._folders:
            if not folder.exists():
                Path.mkdir(folder, parents=True)

    def _check_files(self):
        # config.json
        if not self._path_config_json.exists():
            content = {
                'wallets': [],
                'track': {
                    'mainnet': [],
                    'optimism': [],
                    'polygon': [],
                    'arbitrum': [],
                },
                'ignore': {
                    'mainnet': [],
                    'optimism': [],
                    'polygon': [],
                    'arbitrum': [],
                },
                'alarm': [
                    {
                        'name': '',
                        'pool_id': '',
                        'pool_address': '',
                        'min_tick': 0,
                        'max_tick': 0
                    }
                ]
            }
            json_(self._path_config_json, content, indent='\t')

        # invest.json
        if not self._path_invest_json.exists():
            content = {
                'investiments': [
                    {
                        'amount': 0,
                        'timestamp': 0,
                    }
                ],
            }
            json_(self._path_invest_json, content, indent='\t')

    '''
    PROXIES
    '''
    @property
    def proxy(self):
        return self._proxy

    @property
    def proxies(self):
        if not self._proxy:
            return None
        url = f'http://{self._proxy}'
        return {
            "http": url,
            "https": url,
        }

    def _load_proxies(self):
        self._proxy = self.config_json["proxy"]
        if not self._proxy:  # TODO: validate address format
            return None

    '''
    WALLETS
    '''

    def print_wallet(self, wallet, crop=0, end='\n'):
        if wallet not in self.wallets and wallet != 'track':
            return
        name = self.wallets[wallet] if wallet != 'track' else 'track'
        name = name.upper()
        if crop:
            wallet = wallet[:crop]
        print(f'[bright_white]{name} [bright_black]{wallet}', end=end)

    def print_network(self, network, to_upper=True, end='\n'):
        print(
            f'{self.networks[network]["color"]}{network.upper() if to_upper else network}', end=end)

    def validate_address(self, address):
        if not address:
            return
        try:
            address = Web3.toChecksumAddress(address)
        except ValueError:
            if not address.startswith('#'):  # ignore commented wallets
                print(
                    f'[yellow]Invalid wallet address: [bright_white]{address}')
            address = None
        return address

    def _load_wallets(self):
        return {self.validate_address(x): comment for x, comment in self.config_json['wallets'].items() if self.validate_address(x)}

    def _update_wallets(self):
        wallets = self._load_wallets()
        if not wallets:
            print('[yellow]No valid wallets were found')
            self.add_new_wallet()
            wallets = self._load_wallets()
        self.wallets = wallets

    def add_new_wallet(self):
        while True:
            string = input(
                '[white]Please insert new address [Empty to cancel]\n>').strip()
            if not string:
                return
            address = self.validate_address(string)
            if not address:
                continue
            if address in self.config_json['wallets']:
                print('Wallet already exists')
                continue
            comment = input('[white]Please insert address comment\n>').strip()
            self.config_json['wallets'].add({address: comment})
            self.update_json('config')
            print(
                f'[white]Added wallet: [bright_white]{comment} - [bright_cyan]{address}')


cfg = Config()
