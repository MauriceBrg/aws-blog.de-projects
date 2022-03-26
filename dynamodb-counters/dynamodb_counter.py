import time

import boto3
import boto3.dynamodb.conditions as conditions

from botocore.exceptions import ClientError

TABLE_NAME = "blog_data"

def create_table_if_not_exists():

    try:
        boto3.client("dynamodb").create_table(
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
    except ClientError as err:
        if err.response["Error"]["Code"] == 'ResourceInUseException':
            # Table already exists
            pass
        else:
            raise err
    
    try:
        response = boto3.client("dynamodb").update_time_to_live(
            TableName=TABLE_NAME,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
    except ClientError as err:
        if err.response["Error"]["Code"] == 'ValidationException':
            # Already enabled
            pass
        else:
            raise err

def very_naive_view_counter(view_event: dict, table_name: str):
	table = boto3.resource("dynamodb").Table(table_name)

	blog_url = view_event["url"]

	# Increment the view counter by 1
	table.update_item(
		Key={
			"PK": f"URL#{blog_url}",
			"SK": "STATISTICS"
		},
		UpdateExpression="SET #views = #views + :increment",
		ExpressionAttributeNames={
			"#views": "views"
		},
		ExpressionAttributeValues={
			":increment": 1
		}	
	)

def less_naive_view_counter(view_event: dict, table_name: str):
	table = boto3.resource("dynamodb").Table(table_name)

	blog_url = view_event["url"]

	# Increment the view counter by 1
	table.update_item(
		Key={
			"PK": f"URL#{blog_url}",
			"SK": "STATISTICS"
		},
		UpdateExpression="SET #views = if_not_exists(#views, :init) + :inc",
        ExpressionAttributeNames={
            "#views": "views"
        },
        ExpressionAttributeValues={
            ":inc": 1,
            ":init": 0
        }
	)

def accurate_view_counter(view_event: dict, table_name: str):

    # transactions are only supported using the client API
    client = boto3.client("dynamodb")

    partition_key = f"URL#{view_event['url']}"
    sort_key_stats = "STATISTICS"
    sort_key_event = f"T#{view_event['time']}#CID#{view_event['clientId']}"

    try:
        client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": table_name,
                        "Item": {
                            "PK": {"S": partition_key},
                            "SK": {"S": sort_key_event}
                        },
                        "ConditionExpression": "attribute_not_exists(PK) and attribute_not_exists(SK)"
                    }
                },
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {
                            "PK": {"S": partition_key},
                            "SK": {"S": sort_key_stats}
                        },
                        "UpdateExpression": "SET #views = if_not_exists(#views, :init) + :inc",
                        "ExpressionAttributeNames": {
                            "#views": "views"
                        },
                        "ExpressionAttributeValues": {
                            ":init": {"N": "0"},
                            ":inc": {"N": "1"}
                        }
                    }
                }
            ]
        )
    
    except ClientError as err:
        if err.response["Error"]["Code"] == 'TransactionCanceledException':
            # Already processed
            print("View event was already processed")
        else:
            raise err


def accurate_view_counter_with_ttl(view_event: dict, table_name: str):

    # transactions are only supported using the client API
    client = boto3.client("dynamodb")

    expire_after_seconds = 60 * 60 * 24 * 7 # a week
    current_time_as_epoch = int(time.time())
    expiry_time = current_time_as_epoch + expire_after_seconds


    partition_key = f"URL#{view_event['url']}"
    sort_key_stats = "STATISTICS"
    sort_key_event = f"T#{view_event['time']}#CID#{view_event['clientId']}"

    try:
        client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": table_name,
                        "Item": {
                            "PK": {"S": partition_key},
                            "SK": {"S": sort_key_event},
                            "ttl": {"N": str(expiry_time)}
                        },
                        "ConditionExpression": "attribute_not_exists(PK) and attribute_not_exists(SK)"
                    }
                },
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {
                            "PK": {"S": partition_key},
                            "SK": {"S": sort_key_stats}
                        },
                        "UpdateExpression": "SET #views = if_not_exists(#views, :init) + :inc",
                        "ExpressionAttributeNames": {
                            "#views": "views"
                        },
                        "ExpressionAttributeValues": {
                            ":init": {"N": "0"},
                            ":inc": {"N": "1"}
                        }
                    }
                }
            ]
        )
    
    except ClientError as err:
        if err.response["Error"]["Code"] == 'TransactionCanceledException':
            # Already processed
            print("View event was already processed")
        else:
            raise err


def main():

    create_table_if_not_exists()

    view_event = {
        "url": "myblog.com/article1",
        "time": "2022-03-28T13:17:23+00:00",
        "clientId": "agiaOIkenODSksi92LHd6a"
    }

    # less_naive_view_counter(view_event, TABLE_NAME)
    # very_naive_view_counter(view_event, TABLE_NAME)
    # accurate_view_counter(view_event, TABLE_NAME)
    accurate_view_counter_with_ttl(view_event, TABLE_NAME)

if __name__ == "__main__":
    main()
