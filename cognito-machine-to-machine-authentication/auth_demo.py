import base64
import logging
import requests
import sys

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


# TODO: Replace this with your cognito domain, remember the region
AUTH_DOMAIN = "some-random-domain-2348472435.auth.eu-central-1.amazoncognito.com"
COGNITO_TOKEN_ENDPOINT = f"https://{ AUTH_DOMAIN }/oauth2/token"

# TODO: Replace these with the credentials you take from the GUI 
CLIENT_ID = "gvcaed2brn0i23hiu6sviomvp"
CLIENT_SECRET = "1vh1ptkkcuci4tf6qoc67oi3vc4sdrlp9rsjpd2msab025a8v3gq"

# TODO: Replace these with your own scopes - separated with a space
LIST_OF_SCOPES = "mydomain.com/API_ACCESS"

# TODO: Replace this with your own enpoint URL
API_GW_ENDPOINT = "https://pd6425glvg.execute-api.eu-central-1.amazonaws.com/dev/"


def configure_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s -  %(message)s')
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)


def get_access_token():

    body = {
        "grant_type": "client_credentials",
        "scope": LIST_OF_SCOPES
    }

    LOGGER.debug("Body: %s", body)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(
        url=COGNITO_TOKEN_ENDPOINT,
        data=body,
        auth=(CLIENT_ID, CLIENT_SECRET),
        headers=headers
    )

    LOGGER.debug("Response: %s", response.json())

    return response.json()["access_token"]


def main():

    configure_logging()
    
    access_token = get_access_token()

    headers = {
        "Authorization": access_token
    }

    LOGGER.debug("GETting URL %s", API_GW_ENDPOINT)
    response = requests.get(API_GW_ENDPOINT, headers=headers)

    LOGGER.debug("Response: %s", response.json())

    

if __name__ == "__main__":
    main()