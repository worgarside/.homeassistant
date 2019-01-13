from datetime import timedelta
from os import getenv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.const import LENGTH_METERS

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


def log(m='', newline=False):
    from datetime import datetime
    now = datetime.now()
    with open('/home/homeassistant/.homeassistant/logs/hass_activity_{}-{:02d}-{:02d}.log'.format(now.year, now.month,
                                                                                                  now.day),
              'a') as f:
        if newline:
            f.write('\n')
        f.write('\n[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]: {}'
                .format(now.year, now.month, now.day, now.hour, now.minute, now.second, m)
                )


def _refresh_access_token(access_token):
    from requests import post
    from json import dump

    res = post('https://www.strava.com/oauth/token', headers={'Authorization': 'Bearer {}'.format(access_token)}, json=JSON)
    with open(CLIENT_SECRETS_FILE, 'w') as f:
        dump(res.json(), f)
    return res.json()['access_token']


def _get_data(datum, ytd=False):
    from json import load
    from datetime import datetime
    from requests import get

    def _get_athlete():
        return get('https://www.strava.com/api/v3/athletes/{}/stats'.format(STRAVA_USER_ID),
                   headers={'Authorization': 'Bearer {}'.format(access_token)})

    with open(CLIENT_SECRETS_FILE, 'r') as f:
        client_secrets = load(f)
        access_token = client_secrets['access_token']

    if client_secrets['expires_at'] - 3000 < int(datetime.now().timestamp()):
        access_token = _refresh_access_token(access_token)

    athlete = _get_athlete()

    if 'errors' in athlete.json() and athlete.json()['message'] == 'Authorization Error':
        access_token = _refresh_access_token(access_token)
        athlete = _get_athlete()

    return athlete.json()['ytd_run_totals' if ytd else 'all_run_totals'][datum]


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([CumulativeRunDistanceSensor(), CumulativeRunElevationSensor(), CumulativeRunTimeSensor(),
                 YearToDateRunDistanceSensor(), YearToDateRunElevationSensor(), YearToDateRunTimeSensor()])


class CumulativeRunDistanceSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Cumulative Run Distance'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return LENGTH_METERS

    @Throttle(timedelta(minutes=15))
    def update(self):
        log('Strava: Cumulative Run Distance')
        self._state = _get_data('distance')


class CumulativeRunTimeSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Cumulative Run Time'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'hours'

    @Throttle(timedelta(minutes=15))
    def update(self):
        log('Strava: Cumulative Run Time')
        self._state = round(_get_data('moving_time') / 3600, 2)


class CumulativeRunElevationSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Cumulative Run Elevation'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return LENGTH_METERS

    @Throttle(timedelta(minutes=15))
    def update(self):
        log('Strava: Cumulative Run Elevation')
        self._state = _get_data('elevation_gain')


class YearToDateRunDistanceSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'YTD Run Distance'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return LENGTH_METERS

    @Throttle(timedelta(minutes=15))
    def update(self):
        log('Strava: YTD Run Distance')
        self._state = _get_data('distance', ytd=True)


class YearToDateRunTimeSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'YTD Run Time'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'hours'

    @Throttle(timedelta(minutes=15))
    def update(self):
        log('Strava: YTD Run Time')
        self._state = round(_get_data('moving_time', ytd=True) / 3600, 2)


class YearToDateRunElevationSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'YTD Run Elevation'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return LENGTH_METERS

    @Throttle(timedelta(minutes=15))
    def update(self):
        log('Strava: YTD Run Elevation')
        self._state = _get_data('elevation_gain', ytd=True)
