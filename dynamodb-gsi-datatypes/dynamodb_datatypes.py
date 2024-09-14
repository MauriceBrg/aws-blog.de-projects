import contextlib
import logging
import sys
import time

import boto3
from botocore.exceptions import ClientError

TABLE_NAME = "datatype-demo"
LOGGER = logging.getLogger(__name__)


@contextlib.contextmanager
def log_section(name: str):
    LOGGER.info("\n%s BEGIN %s %s\n", "=" * 10, name, "=" * 10)
    yield
    LOGGER.info("\n%s END %s %s\n", "=" * 11, name, "=" * 11)


def create_table_if_not_exists(client):

    try:
        client.create_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
    except client.exceptions.ResourceInUseException:
        LOGGER.info("Table already exists")
    else:
        LOGGER.info("Table created, waiting for table to become active...")
        client.get_waiter("table_exists").wait(TableName=TABLE_NAME)


def add_gsi(client):

    try:
        client.update_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=[
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    "Create": {
                        "IndexName": "GSI1",
                        "KeySchema": [{"AttributeName": "GSI1PK", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                }
            ],
        )
    except ClientError:
        LOGGER.info("Index already exists")
    else:
        LOGGER.info("Index created, waiting for it to become active...")
        attempt = 0
        while attempt < 50:
            response = client.describe_table(TableName=TABLE_NAME)
            index_status = response["Table"]["GlobalSecondaryIndexes"][0]["IndexStatus"]
            if index_status == "ACTIVE":
                return

            time.sleep(5)
            attempt += 1


def try_put_and_log_error(client, item: dict):

    try:
        client.put_item(TableName=TABLE_NAME, Item=item)
    except ClientError as err:
        LOGGER.error(
            "Error: %s\nMessage: %s",
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
    else:
        LOGGER.info("...done.")


def main():
    LOGGER.addHandler(logging.StreamHandler(sys.stdout))
    LOGGER.addHandler(
        logging.FileHandler("dynamodb_datatypes.log", mode="w", encoding="utf-8")
    )
    LOGGER.setLevel(logging.INFO)

    client = boto3.client("dynamodb")

    create_table_if_not_exists(client)

    with log_section("Putting item with correct datatypes"):
        item_with_correct_datatypes = {
            "PK": {"S": "ok"},
            "GSI1PK": {"S": "ok"},
        }
        LOGGER.info("Putting item with correct datatypes")
        try_put_and_log_error(client, item_with_correct_datatypes)

    with log_section("Putting item with incorrect datatype in base table"):
        item_with_incorrect_datatype_in_base = {
            "PK": {"N": "123"},
            "GSI1PK": {"S": "ok"},
        }
        LOGGER.info("Putting item with incorrect datatype in base table")
        try_put_and_log_error(client, item_with_incorrect_datatype_in_base)

    with log_section(
        "Putting item with incorrect datatype in GSI before the GSI exists"
    ):
        item_with_incorrect_datatype_in_gsi = {
            "PK": {"S": "ok2"},
            "GSI1PK": {"N": "123"},
        }
        LOGGER.info("Putting item with incorrect datatype in GSI before the GSI exists")
        try_put_and_log_error(client, item_with_incorrect_datatype_in_gsi)

        another_item_with_incorrect_datatype_in_gsi = {
            "PK": {"S": "ok3"},
            "GSI1PK": {"N": "123"},
        }
        LOGGER.info(
            "Putting another item with incorrect datatype in GSI before the GSI exists"
        )
        try_put_and_log_error(client, another_item_with_incorrect_datatype_in_gsi)

    LOGGER.info("Adding the GSI to the table")
    add_gsi(client)

    with log_section(
        "Putting item with incorrect datatype in GSI after the GSI exists"
    ):
        yet_another_item_with_incorrect_datatype_in_gsi = {
            "PK": {"S": "ok4"},
            "GSI1PK": {"N": "123"},
        }
        LOGGER.info("Putting item with incorrect datatype in GSI after the GSI exists")
        try_put_and_log_error(client, yet_another_item_with_incorrect_datatype_in_gsi)
        LOGGER.info(
            "We can no longer add items with datatypes that conflict with index attributes."
        )

    with log_section("Scan GSI1"):
        response = client.scan(TableName=TABLE_NAME, IndexName="GSI1")
        LOGGER.info("Items in GSI1: %s", response["Items"])
        LOGGER.info("Only the item with the correct datatypes ends up in GSI1")

    with log_section("Trying to update item with incorrect datatypes"):
        LOGGER.info(
            "Trying to update the item with invalid datatypes in the base table."
        )
        try:
            client.update_item(
                Key={"PK": {"S": "ok2"}},
                UpdateExpression="SET test = :val",
                ExpressionAttributeValues={":val": {"N": "2"}},
                TableName=TABLE_NAME,
            )
        except ClientError as err:
            LOGGER.error(
                "Error: %s\nMessage: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )

    with log_section("Trying to delete item with incorrect datatype"):
        LOGGER.info("Trying to delete one of the items with invalid datatypes")
        client.delete_item(Key={"PK": {"S": "ok3"}}, TableName=TABLE_NAME)
        LOGGER.info("...done")

    with log_section("Try to fix incorrect datatype"):

        LOGGER.info("Trying to set GSI1PK to string value")
        client.update_item(
            Key={"PK": {"S": "ok2"}},
            UpdateExpression="SET GSI1PK = :val",
            ExpressionAttributeValues={":val": {"S": "123"}},
            TableName=TABLE_NAME,
        )
        LOGGER.info("...done")

    LOGGER.info("Deleting table...")
    client.delete_table(TableName=TABLE_NAME)


if __name__ == "__main__":
    main()
