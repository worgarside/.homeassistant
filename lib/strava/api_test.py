from json import dump
from os import getenv
from pprint import pprint

from dotenv import load_dotenv
from requests import post

load_dotenv('/home/homeassistant/.homeassistant/secret_files/.env')

CLIENT_SECRETS_FILE = '/home/homeassistant/.homeassistant/secret_files/strava_client_secrets.json'

STRAVA_USER_ID = getenv('STRAVA_USER_ID')
STRAVA_CLIENT_ID = getenv('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = getenv('STRAVA_CLIENT_SECRET')
STRAVA_REFRESH_TOKEN = getenv('STRAVA_REFRESH_TOKEN')

JSON = {
    'grant_type': 'refresh_token',
    'client_id': STRAVA_CLIENT_ID,
    'client_secret': STRAVA_CLIENT_SECRET,
    'refresh_token': STRAVA_REFRESH_TOKEN
}


def _refresh_access_token(access_token):
    res = post('https://www.strava.com/oauth/token', headers={'Authorization': f'Bearer {access_token}'}, json=JSON)
    with open(CLIENT_SECRETS_FILE, 'w') as f:
        dump(res.json(), f)
    return res.json()['access_token']


def _get_data(datum, ytd=False):
    from json import load
    from datetime import datetime
    from requests import get
    from json.decoder import JSONDecodeError

    def _get_athlete():
        return get('https://www.strava.com/api/v3/athletes/{}/stats'.format(STRAVA_USER_ID),
                   headers={'Authorization': 'Bearer {}'.format(access_token)})

    try:
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            client_secrets = load(f)
            access_token = client_secrets['access_token']

        if client_secrets['expires_at'] - 3000 < int(datetime.now().timestamp()):
            access_token = _refresh_access_token(access_token)
    except (JSONDecodeError, KeyError) as e:
        access_token = 'abcdefghijklmnopqrstuvwxyz'
        _refresh_access_token(access_token)

    athlete = _get_athlete()

    if 'errors' in athlete.json() and athlete.json()['message'] == 'Authorization Error':
        access_token = _refresh_access_token(access_token)
        athlete = _get_athlete()

    return athlete.json()['ytd_run_totals' if ytd else 'all_run_totals'][datum]


if __name__ == '__main__':
    pprint(_get_data('distance'))
