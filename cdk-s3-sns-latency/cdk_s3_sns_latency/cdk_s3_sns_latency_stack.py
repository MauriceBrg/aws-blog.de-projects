import os

import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_lambda_event_sources as lambda_event_sources
import aws_cdk.aws_sns as sns
import aws_cdk.aws_ssm as ssm
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_notifications as s3_notifications

from aws_cdk import core

BUCKET_WITH_LAMBDA_PARAMETER = "/cdk-s3-sns-latency/bucket-with-lambda"
BUCKET_WITH_SNS_PARAMETER = "/cdk-s3-sns-latency/bucket-with-sns"
MEASUREMENT_TABLE_PARAMETER = "/cdk-s3-sns-latency/measurement-table"
GENERATOR_FUNCTION_NAME_PARAMETER = "/cdk-s3-sns-latency/generator-function-name"


class CdkS3SnsLatencyStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        bucket_with_sns = s3.Bucket(
            self,
            "bucket-with-sns-integration",
            removal_policy=core.RemovalPolicy.DESTROY
        )

        bucket_with_lambda = s3.Bucket(
            self,
            "bucket-with-lambda-integration",
            removal_policy=core.RemovalPolicy.DESTROY
        )

        exchange_topic = sns.Topic(
            self,
            "lambda-info-topic"
        )

        bucket_with_sns.add_event_notification(
            event=s3.EventType.OBJECT_CREATED,
            dest=s3_notifications.SnsDestination(exchange_topic)
        )

        measurement_table = dynamodb.Table(
            self,
            "measurement-table",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=core.RemovalPolicy.DESTROY
        )

        s3_event_generator = _lambda.Function(
            self,
            "s3-event-generator",
            code=_lambda.Code.from_asset(
                path=os.path.join(os.path.dirname(__file__), "..", "src")
            ),
            environment={
                "BUCKET_WITH_LAMBDA": bucket_with_lambda.bucket_name,
                "BUCKET_WITH_SNS": bucket_with_sns.bucket_name,
            },
            handler="s3_event_generator.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_8,
            timeout=core.Duration.seconds(300),
            memory_size=1024,
        )

        bucket_with_lambda.grant_write(s3_event_generator)
        bucket_with_sns.grant_write(s3_event_generator)

        measure_lambda = _lambda.Function(
            self,
            "measure-lambda",
            code=_lambda.Code.from_asset(
                path=os.path.join(os.path.dirname(__file__), "..", "src")
            ),
            environment={
                "MEASUREMENT_TABLE": measurement_table.table_name
            },
            handler="measure_lambda.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_8,
            timeout=core.Duration.seconds(50),
            memory_size=1024,
        )

        measurement_table.grant_read_write_data(measure_lambda)

        measure_lambda.add_event_source(
            lambda_event_sources.SnsEventSource(
                exchange_topic
            )
        )

        measure_lambda.add_event_source(
            lambda_event_sources.S3EventSource(
                bucket=bucket_with_lambda,
                events=[s3.EventType.OBJECT_CREATED]
            )
        )

        ssm.StringParameter(
            self,
            "bucket-with-sns-parameter",
            string_value=bucket_with_sns.bucket_name,
            parameter_name=BUCKET_WITH_SNS_PARAMETER
        )

        ssm.StringParameter(
            self,
            "bucket-with-lambda-parameter",
            string_value=bucket_with_lambda.bucket_name,
            parameter_name=BUCKET_WITH_LAMBDA_PARAMETER
        )

        ssm.StringParameter(
            self,
            "measurement-table-parameter",
            string_value=measurement_table.table_name,
            parameter_name=MEASUREMENT_TABLE_PARAMETER
        )

        ssm.StringParameter(
            self,
            "generator-function-name-parameter",
            string_value=s3_event_generator.function_name,
            parameter_name=GENERATOR_FUNCTION_NAME_PARAMETER
        )
