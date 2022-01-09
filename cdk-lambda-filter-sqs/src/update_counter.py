import os

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "sqs-filter-demo-data")

CLIENT = boto3.client("dynamodb")

def lambda_handler(event, context):

    # We don't care about the event, just increment the counter
    CLIENT.update_item(
        TableName=TABLE_NAME,
        Key={
            "PK": {"S": "SUMMARY"}
        },
        UpdateExpression="ADD #counter :counter_increment",
        ExpressionAttributeNames={
            "#counter": "counter",
        },
        ExpressionAttributeValues={
            ":counter_increment": {"N": "1"},
        }
    )
