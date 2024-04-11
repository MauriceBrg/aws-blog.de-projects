# pylint: disable=W0621,W0613
import os

from typing import Iterator
from http import HTTPStatus

import boto3
import dash
import moto
import pytest

from frontend import auth


@pytest.fixture
def cognito_setup() -> Iterator[auth.CognitoInfo]:
    """
    Sets up a Cognito User Pool, App Client, and Custom Domain.
    """

    with moto.mock_aws():

        region = "eu-central-1"
        os.environ["AWS_REGION"] = region

        cognito = boto3.client("cognito-idp")

        response = cognito.create_user_pool(
            PoolName="test",
            AutoVerifiedAttributes=["email"],
        )
        user_pool_id = response["UserPool"]["Id"]

        response = cognito.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName="test_client",
            GenerateSecret=True,
            LogoutURLs=["https://something.com/logout"],
        )

        client_id = response["UserPoolClient"]["ClientId"]
        client_secret = response["UserPoolClient"]["ClientSecret"]

        os.environ[auth.ENV_COGNITO_USER_POOL_ID] = user_pool_id
        os.environ[auth.ENV_COGNITO_REGION] = region
        os.environ[auth.ENV_COGNITO_CLIENT_ID] = client_id

        cognito.create_user_pool_domain(UserPoolId=user_pool_id, Domain="test")

        os.environ[auth.ENV_COGNITO_CUSTOM_DOMAIN] = "test"

        auth_info: auth.CognitoInfo = {
            "client_id": client_id,
            "client_secret": client_secret,
            "logout_urls": ["https://something.com/logout"],
            "region": region,
            "user_pool_id": user_pool_id,
            "domain": "test",
        }

        yield auth_info


@pytest.fixture()
def dash_app() -> dash.Dash:
    """Sample app that just renders Hello World."""

    app = dash.Dash(__name__, url_base_pathname="/prod/")
    app.layout = dash.html.H1("Hello World")

    return app


def test_get_cognito_info(cognito_setup: auth.CognitoInfo):
    """
    Assert that get_cognito_info returns the expected results.
    """

    # Arrange
    expected_info = cognito_setup
    auth.get_cognito_info.cache_clear()

    # Act
    actual_info = auth.get_cognito_info()

    # Assert
    assert actual_info == expected_info


def test_add_cognito_auth_to(cognito_setup, dash_app):
    """
    Ensure authentication is added to the app.
    We should see a redirect to the Cognito endpoint if we're not authenticated.
    """

    # Arrange
    app = dash_app
    test_client = app.server.test_client()

    # Act
    auth.add_cognito_auth_to(app)

    # Assert
    response = test_client.get("/prod/")

    assert response.status_code == HTTPStatus.FOUND
    assert "/prod/login/cognito" == response.location
