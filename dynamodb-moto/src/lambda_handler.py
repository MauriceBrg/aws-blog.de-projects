import os
import boto3
import boto3.dynamodb.conditions as conditions

ENV_TABLE_NAME = "TABLE_NAME"

def get_table_resource():

    dynamodb_resource = boto3.resource("dynamodb")
    table_name = os.environ[ENV_TABLE_NAME]
    return dynamodb_resource.Table(table_name)

def get_transactions_for_client(client_id: str) -> list:
    table = get_table_resource()

    # Get all items in the partition that start with TX#
    response = table.query(
        KeyConditionExpression=\
            conditions.Key("PK").eq(f"CLIENT#{client_id}") \
            & conditions.Key("SK").begins_with(f"TX#") 
    )
    
    return response["Items"]

def save_transaction_summary(summary_item: dict):

    # Add key information
    summary_item["PK"] = f"CLIENT#{summary_item['clientId']}"
    summary_item["SK"] = "SUMMARY"

    # store the item
    table = get_table_resource()
    table.put_item(Item=summary_item)

def lambda_handler(event, context):
    
    client_id = event["clientId"]
    
    client_transactions = get_transactions_for_client(client_id)

    total_sum = sum(tx["total"] for tx in client_transactions)

    summary_item = {
        "clientId": client_id,
        "totalSum": total_sum
    }
    save_transaction_summary(summary_item)

    return summary_item