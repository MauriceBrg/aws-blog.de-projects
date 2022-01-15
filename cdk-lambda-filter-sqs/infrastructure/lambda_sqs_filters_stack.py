import json
import os

from aws_cdk import (
    # Duration,
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_lambda_event_sources as events,
    aws_sqs as sqs,
)
from constructs import Construct

import constants

class LambdaSqsFiltersStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        job_queue = sqs.Queue(
            self,
            "job-queue",
            queue_name=f"{constants.APP_NAME}-queue"
        )

        data_table = dynamodb.Table(
            self,
            "data-table",
            table_name=f"{constants.APP_NAME}-data",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
        )

        update_counter_lambda = _lambda.Function(
            self,
            id="update-counter-lambda",
            function_name=f"{constants.APP_NAME}-update-counter",
            environment={
                "TABLE_NAME": data_table.table_name,
            },
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset(
                path=os.path.join(os.path.dirname(__file__), "..", "src")
            ),
            handler="update_counter.lambda_handler"
        )

        # Filters aren't yet (CDK v2.8.0) supported for DynamoDB, we have to
        # go to the low level CFN stuff here
        _lambda.CfnEventSourceMapping(
            self,
            id="update-counters-event-source",
            function_name=update_counter_lambda.function_name,
            event_source_arn=job_queue.queue_arn,
            batch_size=1,
            filter_criteria={
                "Filters": [
                    {
                        "Pattern": json.dumps({
                            "messageAttributes": {"process_with_lambda": {"stringValue": ["1"]}},
                        })
                    }
                ]
            }
        )

        data_table.grant_read_write_data(update_counter_lambda)
        job_queue.grant_consume_messages(update_counter_lambda)
