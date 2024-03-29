"""
Unit tests for the basic auth lambda handler
"""

import os
import json

import boto3
import pytest
from moto import mock_aws

from basic_auth_authorizer import basic_auth


@pytest.fixture()
def aws_resources():

    os.environ[basic_auth.ENV_SSM_CREDENTIAL_PARAMETER_NAME] = "dummy/parameter"
    os.environ[basic_auth.ENV_SECRETSMANAGER_CREDENTIAL_SECRET_NAME] = "dummy/parameter"

    with mock_aws():
        boto3.client("ssm").put_parameter(
            Name="dummy/parameter", Value='{"dummy": "credentials"}', Type="String"
        )

        boto3.client("secretsmanager").create_secret(
            Name="dummy/parameter", SecretString='{"dummy": "credentials"}'
        )

        yield


@pytest.fixture()
def static_credentials():
    """
    Add hardcoded credentials.
    """
    basic_auth.CREDENTIAL_PROVIDER_NAME_TO_CREDENTIAL_PROVIDER["TEST"] = lambda: {
        "avoid": "using_me"
    }
    curr_value = os.environ.get(basic_auth.ENV_CREDENTIAL_PROVIDER_NAME)
    os.environ[basic_auth.ENV_CREDENTIAL_PROVIDER_NAME] = "TEST"

    yield

    os.environ[basic_auth.ENV_CREDENTIAL_PROVIDER_NAME] = curr_value or ""


def _load_json_event(name: str) -> dict:
    events_dir = os.path.join(os.path.dirname(__file__), "..", "..", "events")

    with open(os.path.join(events_dir, name), encoding="utf-8") as f:
        return json.load(f)


def test_basic_auth_with_valid_credentials(static_credentials):
    """
    Test that we get the expected policy if the credentials are correct.
    """

    # Arrange

    event = _load_json_event("authorizer_valid_credentials.json")
    expected_response = {
        "principalId": "avoid",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Allow",
                    "Resource": "arn:aws:execute-api:eu-west-1:123123123123:2bwhgeifik/Prod/*",
                }
            ],
        },
    }

    # Act
    actual_response = basic_auth.lambda_handler(event, "")

    # Assert
    assert actual_response == expected_response


def test_basic_auth_with_invalid_credentials(static_credentials):
    """
    Test that we get unauthorized for invalid credentials
    """

    # Arrange

    event = _load_json_event("authorizer_invalid_credentials.json")
    expected_response = "Unauthorized"

    # Act
    actual_response = basic_auth.lambda_handler(event, "")

    # Assert
    assert actual_response == expected_response


def test_basic_auth_with_broken_authorization_token(static_credentials):
    """
    Test that we get unauthorized for a broken authorization string
    """

    # Arrange

    event = _load_json_event("authorizer_broken_authorization_token.json")
    expected_response = "Unauthorized"

    # Act
    actual_response = basic_auth.lambda_handler(event, "")

    # Assert
    assert actual_response == expected_response


def test_get_credentials_from_ssm_parameter(aws_resources):
    """
    Test that the correct credentials are read + decoded from the SSM Parameter
    """

    # Arrange
    basic_auth.get_credentials_from_ssm_parameter.cache_clear()

    # Act
    credentials = basic_auth.get_credentials_from_ssm_parameter()

    # Assert
    assert credentials == {"dummy": "credentials"}


def test_get_credentials_from_secrets_manager(aws_resources):
    """
    Test that the correct credentials are read + decoded from the Secretsmanager Secret
    """

    # Arrange
    basic_auth.get_credentials_from_secrets_manager.cache_clear()

    # Act
    credentials = basic_auth.get_credentials_from_secrets_manager()

    # Assert
    assert credentials == {"dummy": "credentials"}
