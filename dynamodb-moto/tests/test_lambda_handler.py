import os

import boto3
import moto
import pytest

import lambda_handler

TABLE_NAME = "data"

@pytest.fixture
def lambda_environment():
    os.environ[lambda_handler.ENV_TABLE_NAME] = TABLE_NAME

@pytest.fixture
def data_table():
    with moto.mock_dynamodb():
        client = boto3.client("dynamodb")
        client.create_table(
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"}
            ],
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )

        yield TABLE_NAME

@pytest.fixture
def data_table_with_transactions(data_table):
    """Creates transactions for a client with a total of 9"""

    table = boto3.resource("dynamodb").Table(data_table)

    txs = [
        {"PK": "CLIENT#123", "SK": "TX#a", "total": 3},
        {"PK": "CLIENT#123", "SK": "TX#b", "total": 3},
        {"PK": "CLIENT#123", "SK": "TX#c", "total": 3},
    ]

    for tx in txs:
        table.put_item(Item=tx)

def get_client_total_sum(client_id: str):

    table = boto3.resource("dynamodb").Table(TABLE_NAME)

    try:
        response = table.get_item(
            Key={
                "PK": f"CLIENT#{client_id}",
                "SK": "SUMMARY"
            }
        )
        return response["Item"]["totalSum"]
    except KeyError:
        return 0

def test_lambda_no_tx_client(lambda_environment, data_table):
    """Tests the lambda function for a client that has no transactions."""
    
    response = lambda_handler.lambda_handler({"clientId": "ABC"}, {})
    expected_sum = 0

    assert response["totalSum"] == expected_sum
    assert get_client_total_sum("ABC") == expected_sum

def test_lambda_with_tx_client(lambda_environment, data_table_with_transactions):
    """
    Tests the lambda function for a client that has some transactions.
    Their total value is 9.
    """
    
    response = lambda_handler.lambda_handler({"clientId": "123"}, {})

    expected_sum = 9

    assert response["totalSum"] == expected_sum
    assert get_client_total_sum("123") == expected_sum
