# Adapted from https://github.com/aws-samples/aws-secrets-manager-rotation-lambdas/blob/master/SecretsManagerRotationTemplate/lambda_function.py

import json
import logging
import os
import typing

from datetime import datetime, timedelta
from time import sleep

import boto3

ENV_IAM_USERNAME = "IAM_USERNAME"
ENV_DELETE_OLD_AFTER_N_MINUTES = "DELETE_OLD_AFTER_N_MINUTES"
ENV_SCHEDULER_ROLE_ARN = "SCHEDULER_ROLE_ARN"

SecretsManagerEvent = typing.TypedDict(
    "SecretsManagerEvent",
    {
        "SecretId": str,
        "ClientRequestToken": str,
        "Step": typing.Literal[
            "createSecret",
            "setSecret",
            "testSecret",
            "finishSecret",
            "deletePreviousSecret",
        ],
    },
)

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def lambda_handler(event: SecretsManagerEvent, context):
    """
    Custom secret rotation with a grace period for IAM user access keys.
    """
    arn = event["SecretId"]
    token = event["ClientRequestToken"]
    step = event["Step"]

    LOGGER.info("Step: %s", step)

    # Setup the client
    secretsmanager_client = boto3.client("secretsmanager")

    # Make sure the version is staged correctly
    metadata = secretsmanager_client.describe_secret(SecretId=arn)
    if not metadata["RotationEnabled"]:
        LOGGER.error("Secret %s is not enabled for rotation", arn)
        raise ValueError(f"Secret {arn} is not enabled for rotation")

    if step == "createSecret":
        create_secret(secretsmanager_client, arn, token)

    elif step == "setSecret":
        set_secret()

    elif step == "testSecret":
        test_secret(secretsmanager_client, arn)

    elif step == "finishSecret":
        finish_secret(secretsmanager_client, arn, token, context.invoked_function_arn)

    elif step == "deletePreviousSecret":
        delete_previous_secret(secretsmanager_client, arn)

    else:
        raise ValueError("Invalid step parameter")


def create_secret(service_client, arn, token):
    """
    Create a new access key for the IAM user and store the credentials
    as the AWSPENDING stage in the secret.
    """
    try:
        service_client.get_secret_value(
            SecretId=arn, VersionId=token, VersionStage="AWSPENDING"
        )
        LOGGER.info("createSecret: Successfully retrieved secret for %s.", arn)
    except service_client.exceptions.ResourceNotFoundException:
        iam_username = os.environ.get(ENV_IAM_USERNAME)

        iam_client = boto3.client("iam")
        access_key_response = iam_client.create_access_key(
            UserName=iam_username,
        )

        secret = {
            "username": access_key_response["AccessKey"]["UserName"],
            "access_key_id": access_key_response["AccessKey"]["AccessKeyId"],
            "secret_access_key": access_key_response["AccessKey"]["SecretAccessKey"],
            "create_date": access_key_response["AccessKey"]["CreateDate"].isoformat(),
        }

        # Put the secret
        service_client.put_secret_value(
            SecretId=arn,
            ClientRequestToken=token,
            SecretString=json.dumps(secret),
            VersionStages=["AWSPENDING"],
        )
        LOGGER.info(
            "createSecret: Successfully put secret for ARN %s and version %s.",
            arn,
            token,
        )


def set_secret():
    """
    It takes a few seconds for the new keys to propagate and be accepted as
    valid so we just wait a little bit.
    """
    LOGGER.info("Waiting 10s for the secrets to propagate")
    sleep(10)


def test_secret(service_client, arn):
    """
    Ensure that the credentials in AWSPENDING are valid and belong to the
    IAM user we expect.
    """

    # Get the new credentials
    secret_response = service_client.get_secret_value(
        SecretId=arn, VersionStage="AWSPENDING"
    )

    # Instantiate sts client with the new credentials
    creds = json.loads(secret_response["SecretString"])
    sts_client = boto3.client(
        "sts",
        aws_access_key_id=creds["access_key_id"],
        aws_secret_access_key=creds["secret_access_key"],
    )

    # Ensure they're valid by testing that they belong to our user.
    caller_identity = sts_client.get_caller_identity()
    assert caller_identity["Arn"].endswith(
        "user/" + os.environ.get(ENV_IAM_USERNAME)
    ), f"{caller_identity['Arn']} doesn't end with user/{os.environ.get(ENV_IAM_USERNAME)}"


def finish_secret(service_client, arn, token, lambda_arn):
    """
    Promote the AWSPENDING secret to AWSCURRENT and create a schedule that
    later deletes the AWSPREVIOUS access key in IAM.
    """
    # First describe the secret to get the current version
    metadata = service_client.describe_secret(SecretId=arn)
    current_version = None
    for version in metadata["VersionIdsToStages"]:
        if "AWSCURRENT" in metadata["VersionIdsToStages"][version]:
            if version == token:
                # The correct version is already marked as current, return
                LOGGER.info(
                    "finishSecret: Version %s already marked as AWSCURRENT for %s",
                    version,
                    arn,
                )
                return
            current_version = version
            break

    # Finalize by staging the secret version current
    service_client.update_secret_version_stage(
        SecretId=arn,
        VersionStage="AWSCURRENT",
        MoveToVersionId=token,
        RemoveFromVersionId=current_version,
    )
    LOGGER.info(
        "finishSecret: Successfully set AWSCURRENT stage to version %s for secret %s.",
        token,
        arn,
    )

    # Calculate when to delete the old credentials
    delete_in_n_minutes = int(os.environ.get(ENV_DELETE_OLD_AFTER_N_MINUTES, "5"))
    deletion_timestamp = (
        datetime.now() + timedelta(minutes=delete_in_n_minutes)
    ).isoformat(timespec="seconds")
    username = os.environ.get(ENV_IAM_USERNAME)

    LOGGER.info(
        "Deleting previous access key for %s in %s minutes (%s)",
        username,
        delete_in_n_minutes,
        deletion_timestamp,
    )

    # Schedule the deletion of the old credentials
    scheduler_client = boto3.client("scheduler")
    scheduler_client.create_schedule(
        Name=f"DeletePreviousAKFor{username}",
        ScheduleExpression=f"at({deletion_timestamp})",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": lambda_arn,
            "RoleArn": os.environ.get(ENV_SCHEDULER_ROLE_ARN),
            "Input": json.dumps(
                {
                    "Step": "deletePreviousSecret",
                    "ClientRequestToken": "not_relevant_for_next_step",
                    "SecretId": arn,
                }
            ),
        },
    )


def delete_previous_secret(secretsmanager_client, arn):
    """
    Delete the access key labeled with AWSPREVIOUS and also the
    schedule that triggered the Lambda function so we're ready
    for another secret rotation.
    """

    # Get the previous access key id
    secret_response = secretsmanager_client.get_secret_value(
        SecretId=arn, VersionStage="AWSPREVIOUS"
    )
    creds = json.loads(secret_response["SecretString"])
    access_key_id = creds["access_key_id"]

    # Delete the old access key
    iam_client = boto3.client("iam")
    username = os.environ.get(ENV_IAM_USERNAME)
    iam_client.delete_access_key(
        UserName=username,
        AccessKeyId=access_key_id,
    )
    LOGGER.info("Deleted Access Key %s... for User %s", access_key_id[:8], username)

    # Delete the schedule that triggered us.
    scheduler_client = boto3.client("scheduler")
    scheduler_client.delete_schedule(
        Name=f"DeletePreviousAKFor{username}",
    )
    LOGGER.info("Cleaning up the deletion schedule")
