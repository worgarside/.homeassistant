from wg_utilities.helpers.functions import get_proj_dirs
from wg_utilities.references.constants import HOMEASSISTANT
from os import path, getenv
from requests import get, post
from dotenv import load_dotenv
from pprint import pprint
from json import load, dump

PROJECT_DIR, SECRET_FILES_DIR, ENV_FILE = get_proj_dirs(path.abspath(__file__), HOMEASSISTANT)

CREDENTIALS_FILE = SECRET_FILES_DIR + 'monzo_client_secrets.json'

load_dotenv(ENV_FILE)

MONZO_CLIENT_SECRET = getenv('MONZO_CLIENT_SECRET')
ENDPOINT = 'https://api.monzo.com/'


def authorize():
    with open(CREDENTIALS_FILE) as f:
        secrets = load(f)

    credentials = {
        'grant_type': 'refresh_token',
        'client_secret': MONZO_CLIENT_SECRET,
        'client_id': secrets['client_id'],
        'refresh_token': secrets['refresh_token']
    }

    r1 = get(f'{ENDPOINT}accounts', headers={'Authorization': f"Bearer {secrets['access_token']}"})

    if r1.status_code == 401:
        res = post('https://api.monzo.com/oauth2/token', data=credentials)
        secrets = res.json()

        with open(CREDENTIALS_FILE, 'w') as f:
            dump(secrets, f)

    return secrets['access_token']


def get_accounts(h):
    return get(f'{ENDPOINT}accounts', headers=h).json()


def get_balance(h, a):
    return get(f'{ENDPOINT}balance?account_id={a}', headers=h).json()


def get_pots(h):
    return get(f'{ENDPOINT}pots', headers=h).json()


def main():
    token = authorize()
    headers = {'Authorization': f'Bearer {token}'}
    # pprint(get_accounts(headers))
    pprint(get_balance(headers, 'acc_00009Q7s9yWS7wBQ8lKjfF'))


if __name__ == '__main__':
    main()
