"""Builds the infrastructure for the experiment"""

import os

import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_lambda_event_sources as lambda_event_sources
import aws_cdk.aws_sns as sns
import aws_cdk.aws_s3 as s3

from aws_cdk import core

LAMBDA_MEMORY_MIN_SIZE_IN_MB = 128
LAMBDA_MEMORY_INCREMENTS_IN_MB = 128
LAMBDA_MEMORY_MAX_SIZE_IN_MB = 2048

class CdkDynamoDBLargeItemsStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        invoker_topic = sns.Topic(self, "experiment-invoker")

        experiment_table = dynamodb.Table(
            self,
            id="experiment-table",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        lambda_code_asset = _lambda.Code.from_asset(
            path=os.path.join(
                os.path.dirname(__file__),
                "..",
                "src"
            )
        )

        # Now we build as many lambdas as we need.
        current_mem_size = LAMBDA_MEMORY_MIN_SIZE_IN_MB

        while current_mem_size <= LAMBDA_MEMORY_MAX_SIZE_IN_MB:

            # Build the function to test the client call
            client_function = _lambda.Function(
                self,
                id=f"measurement-client-{current_mem_size}-mb",
                code=lambda_code_asset,
                environment={
                    "TEST_METHOD": "client",
                    "MEMORY_SIZE": str(current_mem_size),
                    "TABLE_NAME": experiment_table.table_name,
                },
                handler="lambda_handler.client_handler",
                runtime=_lambda.Runtime.PYTHON_3_8,
                memory_size=current_mem_size,
                timeout=core.Duration.seconds(120),
            )

            client_function.add_event_source(
                lambda_event_sources.SnsEventSource(invoker_topic)
            )

            experiment_table.grant_read_write_data(client_function)

            # Allow for self-mutating function
            client_function.add_to_role_policy(
                iam.PolicyStatement(
                    actions=[
                        "lambda:getFunctionConfiguration",
                        "lambda:updateFunctionConfiguration",
                    ],
                    # CFN screams at me with circular dependencies if I use the ref here.
                    resources=["*"]
                )
            )

            # Build the function to test the resource call
            resource_function = _lambda.Function(
                self,
                id=f"measurement-resource-{current_mem_size}-mb",
                code=lambda_code_asset,
                environment={
                    "TEST_METHOD": "resource",
                    "MEMORY_SIZE": str(current_mem_size),
                    "TABLE_NAME": experiment_table.table_name
                },
                handler="lambda_handler.resource_handler",
                runtime=_lambda.Runtime.PYTHON_3_8,
                memory_size=current_mem_size,
                timeout=core.Duration.seconds(120),
            )

            resource_function.add_event_source(
                lambda_event_sources.SnsEventSource(invoker_topic)
            )

            experiment_table.grant_read_write_data(resource_function)

            # Allow for self-mutating function
            resource_function.add_to_role_policy(
                iam.PolicyStatement(
                    actions=[
                        "lambda:getFunctionConfiguration",
                        "lambda:updateFunctionConfiguration",
                    ],
                    # CFN screams at me with circular dependencies if I use the ref here.
                    resources=["*"]
                )
            )

            current_mem_size += LAMBDA_MEMORY_INCREMENTS_IN_MB

        # The function to gather and aggregate the measurements
        result_aggregator = _lambda.Function(
            self,
            id="result-aggregator",
            code=lambda_code_asset,
            environment={
                "TABLE_NAME": experiment_table.table_name,
            },
            handler="lambda_handler.result_aggregator",
            runtime=_lambda.Runtime.PYTHON_3_8,
            memory_size=1024,
            timeout=core.Duration.seconds(300),
        )

        experiment_table.grant_read_write_data(result_aggregator)

        # The function to gather and aggregate the measurements
        invoker = _lambda.Function(
            self,
            id="experiment-invoker-function",
            code=lambda_code_asset,
            environment={
                "INVOKER_TOPIC_ARN": invoker_topic.topic_arn,
                "TABLE_NAME": experiment_table.table_name,
            },
            handler="lambda_handler.invoke_handler",
            runtime=_lambda.Runtime.PYTHON_3_8,
            memory_size=1024,
            timeout=core.Duration.seconds(300),
        )

        invoker_topic.grant_publish(invoker)
        experiment_table.grant_read_write_data(invoker)

        core.CfnOutput(
            self,
            "invokerFn",
            value=invoker.function_name,
            description="Name of the invoker function"
        )

        core.CfnOutput(
            self,
            "resultAggregatorFn",
            value=result_aggregator.function_name,
            description="Name of the result aggregator function"
        )