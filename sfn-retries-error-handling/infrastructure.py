from aws_cdk import (
    Duration,
    Stack,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
)
from constructs import Construct

TABLE_NAME = "sfn-retries-demo"
PK_ATTR = "pk"
SK_ATTR = "sk"


class SfnRetriesErrorHandlingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        table_name = TABLE_NAME
        pk_attr = PK_ATTR
        sk_attr = SK_ATTR

        create_table_if_not_exists = sfn_tasks.CallAwsService(
            self,
            "Create Table if not exists",
            action="createTable",
            service="dynamodb",
            iam_resources=["*"],
            parameters={
                "AttributeDefinitions": [
                    {"AttributeName": pk_attr, "AttributeType": "S"},
                    {"AttributeName": sk_attr, "AttributeType": "S"},
                ],
                "BillingMode": "PAY_PER_REQUEST",
                "TableName": table_name,
                "KeySchema": [
                    {"AttributeName": pk_attr, "KeyType": "HASH"},
                    {"AttributeName": sk_attr, "KeyType": "RANGE"},
                ],
            },
        )

        put_item = sfn_tasks.CallAwsService(
            self,
            "Create Item with Counter = 0",
            action="putItem",
            service="dynamodb",
            iam_resources=[
                "*",  # TODO: This should be restricted to the newly created table
            ],
            parameters={
                "Item": {
                    pk_attr: {"S": "dummy"},
                    sk_attr: {"S": "dummy"},
                    "counter": {"N": "0"},
                },
                "TableName": table_name,
            },
        )

        create_table_if_not_exists.add_catch(
            handler=put_item,
            errors=["DynamoDb.ResourceInUseException"],
        )

        # This means we'll retry after 3, 6, 12 and 24 seconds. Usually the
        # table should be available by then.
        put_item.add_retry(
            errors=[
                "DynamoDb.ResourceNotFoundException",  # Table not active yet
            ],
            backoff_rate=2,
            interval=Duration.seconds(3),
            max_attempts=4,
        )

        increment_counter = sfn_tasks.CallAwsService(
            self,
            "Increment Counter",
            action="updateItem",
            service="dynamodb",
            iam_resources=[
                "*",  # TODO: This should be restricted to the newly created table
            ],
            parameters={
                "Key": {
                    pk_attr: {"S": "dummy"},
                    sk_attr: {"S": "dummy"},
                },
                "TableName": table_name,
                "UpdateExpression": "ADD #counter :inc ",
                "ExpressionAttributeNames": {"#counter": "counter"},
                "ExpressionAttributeValues": {":inc": {"N": "1"}},
            },
        )

        delete_item_if_counter_reaches_limit = sfn_tasks.CallAwsService(
            self,
            "Delete Item if Counter = 2",
            action="deleteItem",
            service="dynamodb",
            iam_resources=[
                "*",  # TODO: This should be restricted to the newly created table
            ],
            parameters={
                "Key": {
                    pk_attr: {"S": "dummy"},
                    sk_attr: {"S": "dummy"},
                },
                "TableName": table_name,
                "ConditionExpression": "#counter = :limit",
                "ExpressionAttributeNames": {"#counter": "counter"},
                "ExpressionAttributeValues": {":limit": {"N": "2"}},
            },
        )

        delete_item_if_counter_reaches_limit.add_catch(
            handler=increment_counter,
            errors=["DynamoDb.ConditionalCheckFailedException"],
        )

        delete_table = sfn_tasks.CallAwsService(
            self,
            "Delete Table",
            action="deleteTable",
            service="dynamodb",
            iam_resources=[
                "*",  # TODO: This should be restricted to the newly created table
            ],
            parameters={
                "TableName": table_name,
            },
        )

        create_table_if_not_exists.next(put_item)
        put_item.next(delete_item_if_counter_reaches_limit)
        increment_counter.next(delete_item_if_counter_reaches_limit)
        delete_item_if_counter_reaches_limit.next(delete_table)

        sfn.StateMachine(
            self,
            id="sfn-errors-and-retries",
            comment="State Machine to Demo Retries and Error Catchers",
            definition_body=sfn.DefinitionBody.from_chainable(
                create_table_if_not_exists
            ),
            state_machine_name="SfnErrorsAndRetriesDemo",
        )
