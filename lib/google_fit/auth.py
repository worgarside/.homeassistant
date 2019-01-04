from json import dump

from google_auth_oauthlib.flow import Flow

CLIENT_SECRETS_FILE = 'secret_files/google_client_secrets.json'
CREDENTIALS_FILE = 'secret_files/google_credentials.json'

SCOPES = ['https://www.googleapis.com/auth/fitness.activity.read',
          'https://www.googleapis.com/auth/fitness.body.read',
          'https://www.googleapis.com/auth/fitness.location.read',
          'https://www.googleapis.com/auth/fitness.nutrition.read']

REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'


def authorize():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    authorization_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true')

    print(authorization_url)
    flow.fetch_token(code=input('Code: ').strip())
    save_credentials(flow.credentials)


def save_credentials(credentials):
    cred_dict = {'token': credentials.token,
                 'refresh_token': credentials.refresh_token,
                 'token_uri': credentials.token_uri,
                 'client_id': credentials.client_id,
                 'client_secret': credentials.client_secret,
                 'scopes': credentials.scopes}

    with open(CREDENTIALS_FILE, 'w') as f:
        dump(cred_dict, f)


if __name__ == '__main__':
    authorize()
