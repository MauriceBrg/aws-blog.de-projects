import typing

from datetime import datetime, timedelta
import boto3
from boto3.dynamodb import conditions

TABLE_NAME = "locks"


def acquire_lock(
    resource_name: str, timeout_in_seconds: int, transaction_id: str
) -> bool:

    dynamodb = boto3.resource("dynamodb")
    ex = dynamodb.meta.client.exceptions
    table = dynamodb.Table(TABLE_NAME)

    now = datetime.now().isoformat(timespec="seconds")
    new_timeout = (datetime.now() + timedelta(seconds=timeout_in_seconds)).isoformat(
        timespec="seconds"
    )

    try:

        table.update_item(
            Key={"PK": "LOCK", "SK": f"RES#{resource_name}"},
            UpdateExpression="SET #tx_id = :tx_id, #timeout = :timeout",
            ExpressionAttributeNames={
                "#tx_id": "transaction_id",
                "#timeout": "timeout",
            },
            ExpressionAttributeValues={
                ":tx_id": transaction_id,
                ":timeout": new_timeout,
            },
            ConditionExpression=conditions.Or(
                conditions.Attr("SK").not_exists(),  # New Item, i.e. no lock
                conditions.Attr("timeout").lt(now),  # Old lock is timed out
            ),
        )

        return True

    except ex.ConditionalCheckFailedException:
        # It's already locked
        return False


def release_lock(resource_name: str, transaction_id: str) -> bool:

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    ex = dynamodb.meta.client.exceptions

    try:
        table.delete_item(
            Key={"PK": "LOCK", "SK": f"RES#{resource_name}"},
            ConditionExpression=conditions.Attr("transaction_id").eq(transaction_id),
        )
        return True

    except (ex.ConditionalCheckFailedException, ex.ResourceNotFoundException):
        return False
