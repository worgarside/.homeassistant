from datetime import datetime
from json import load
from time import mktime

CLIENT_SECRETS_FILE = '../../secret_files/google_client_secrets.json'
CREDENTIALS_FILE = '../../secret_files/google_credentials.json'

USER_ID = 'me'
API_SERVICE_NAME = 'fitness'
API_VERSION = 'v1'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
SCOPES = ['https://www.googleapis.com/auth/fitness.activity.read',
          'https://www.googleapis.com/auth/fitness.body.read',
          'https://www.googleapis.com/auth/fitness.location.read',
          'https://www.googleapis.com/auth/fitness.nutrition.read']
MAX_RETRIES = 5

NOW = int(datetime.now().timestamp())
NOW_NANO = NOW * 1000000000
DAY_START = int(mktime(datetime.today().date().timetuple()) * 1000000000)
ONE_HOUR_AGO = (NOW - 3600) * 1000000000
TWO_MINS_AGO = (NOW - 120) * 1000000000


def _get_client():
    from json import dump
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from time import sleep
    from ssl import SSLEOFError

    with open(CREDENTIALS_FILE, 'r') as f:
        credentials_dict = load(f)

    updated_credentials = Credentials(
        credentials_dict['token'],
        credentials_dict['refresh_token'],
        '',
        credentials_dict['token_uri'],
        credentials_dict['client_id'],
        credentials_dict['client_secret'],
        credentials_dict['scopes']
    )
    with open(CREDENTIALS_FILE, 'w') as f:
        dump({'token': updated_credentials.token,
              'refresh_token': updated_credentials.refresh_token,
              'token_uri': updated_credentials.token_uri,
              'client_id': updated_credentials.client_id,
              'client_secret': updated_credentials.client_secret,
              'scopes': updated_credentials.scopes}, f)

    retry_count = 0
    while True:
        try:
            client = build(API_SERVICE_NAME, API_VERSION, credentials=updated_credentials, cache_discovery=False)
            return client
        except SSLEOFError as e:
            sleep(2.5)
            if retry_count < MAX_RETRIES:
                retry_count += 1
                continue
            else:
                raise SSLEOFError(e)


def _get_dataset(data_source, dataset):
    from ssl import SSLEOFError
    from time import sleep

    client = _get_client()

    retry_count = 0
    while True:
        try:
            dataset = client.users().dataSources().datasets(). \
                get(userId=USER_ID, dataSourceId=data_source, datasetId=dataset).execute()
            return dataset
        except SSLEOFError as e:
            sleep(2.5)
            if retry_count < MAX_RETRIES:
                retry_count += 1
                continue
            else:
                raise SSLEOFError(e)


def _get_available_datasets(client):
    from ssl import SSLEOFError
    from time import sleep

    retry_count = 0
    while True:
        try:
            return client.users().dataSources().list(userId=USER_ID).execute()
        except SSLEOFError as e:
            sleep(2.5)
            if retry_count < MAX_RETRIES:
                retry_count += 1
                continue
            else:
                raise SSLEOFError(e)


def get_daily_step_count():
    _data_source = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
    _dataset = '{}-{}'.format(DAY_START, NOW_NANO)

    dataset = _get_dataset(_data_source, _dataset)

    step_count = 0
    for point in dataset['point']:
        if int(point['startTimeNanos']) > DAY_START:
            step_count += point['value'][0]['intVal']

    return step_count


def get_body_weight():
    _state = None

    _google_fit_data_source = 'raw:com.google.weight:com.google.android.apps.fitness:user_input'
    _myfitnesspal_data_source = 'raw:com.google.weight:com.myfitnesspal.android:'
    _dataset = '{}-{}'.format(DAY_START, NOW_NANO)

    google_fit_dataset = _get_dataset(_google_fit_data_source, _dataset)
    myfitnesspal_dataset = _get_dataset(_myfitnesspal_data_source, _dataset)

    combined_datapoints = google_fit_dataset['point'] + myfitnesspal_dataset['point']

    if len(combined_datapoints) == 1:
        _state = combined_datapoints[0]['value'][0]['fpVal']
    elif len(combined_datapoints) > 1:
        max_time = 0
        weight = 0
        for point in combined_datapoints:
            if float(point['endTimeNanos']) > max_time:
                max_time = float(point['endTimeNanos'])
                weight = point['value'][0]['fpVal']
        _state = round(weight, 2) if not weight == 0 else _state

    return _state


def get_calories_expended():
    _data_source = 'derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended'
    _dataset = '{}-{}'.format(DAY_START, NOW_NANO)

    dataset = _get_dataset(_data_source, _dataset)

    cal_count = 0
    for point in dataset['point']:
        if int(point['startTimeNanos']) > DAY_START:
            cal_count += point['value'][0]['fpVal']

    return int(cal_count)


if __name__ == '__main__':
    print(f'Steps: {get_daily_step_count()}')
    print(f'Weight: {get_body_weight()}')
    print(f'Calories Expended: {get_calories_expended()}')
