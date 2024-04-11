import functools
import os
import typing

import boto3
import dash_cognito_auth as dca

from dash import Dash

ENV_COGNITO_USER_POOL_ID = "COGNITO_USER_POOL_ID"
ENV_COGNITO_REGION = "COGNITO_REGION"
ENV_COGNITO_CLIENT_ID = "COGNITO_CLIENT_ID"
ENV_COGNITO_CUSTOM_DOMAIN = "COGNITO_CUSTOM_DOMAIN"


class CognitoInfo(typing.TypedDict):
    user_pool_id: str
    client_id: str
    client_secret: str
    domain: str
    region: str
    logout_urls: list[str]


@functools.lru_cache(maxsize=1)
def get_cognito_info() -> CognitoInfo:
    """Returns a CognitoInfo-TypedDict and cashes the result."""

    client = boto3.client("cognito-idp")

    user_pool_client = client.describe_user_pool_client(
        UserPoolId=os.environ[ENV_COGNITO_USER_POOL_ID],
        ClientId=os.environ[ENV_COGNITO_CLIENT_ID],
    )["UserPoolClient"]

    user_pool = client.describe_user_pool(
        UserPoolId=os.environ[ENV_COGNITO_USER_POOL_ID],
    )["UserPool"]

    # Either the prefix if hosted in Cognito namespace or the FQDN if custom
    user_pool_domain = user_pool.get("Domain", user_pool.get("CustomDomain"))

    if user_pool_domain is None:
        raise RuntimeError("User Pool doesn't have a domain configured!")

    return {
        "user_pool_id": os.environ[ENV_COGNITO_USER_POOL_ID],
        "client_id": os.environ[ENV_COGNITO_CLIENT_ID],
        "client_secret": user_pool_client["ClientSecret"],
        "domain": user_pool_domain,
        "logout_urls": user_pool_client["LogoutURLs"],
        "region": os.environ[ENV_COGNITO_REGION],
    }


def add_cognito_auth_to(app: Dash) -> None:
    """
    Wrap a Dash app with Cognito authentication.
    """

    info = get_cognito_info()

    app.server.config["COGNITO_OAUTH_CLIENT_ID"] = info["client_id"]
    app.server.config["COGNITO_OAUTH_CLIENT_SECRET"] = info["client_secret"]

    dca.CognitoOAuth(
        app=app, domain=info["domain"], region=info["region"], logout_url="/logout"
    )
