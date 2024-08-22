import base64
import json
import os

from aws_cdk import (
    # Duration,
    Stack,
    CfnOutput,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_lambda as _lambda,
    aws_lambda_destinations as lambda_destinations
)
from constructs import Construct

SRC_PATH = os.path.join(os.path.dirname(__file__), "..", "src")

def dict_to_json_to_b64_str(input_dict: dict) -> str:
    json_str = json.dumps(input_dict)
    b64_bytes = base64.b64encode(json_str.encode("utf-8"))
    return b64_bytes.decode("utf-8")

class CdkLambdaDestinationsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        fifo_queue = sqs.Queue(
            self,
            "fifo-queue",
            fifo=True,
            queue_name="myfifoqueue.fifo"
        )

        fifo_topic = sns.Topic(
            self,
            "fifo-topic",
            fifo=True,
            topic_name="myfifotopic"
        )

        code_asset = _lambda.Code.from_asset(SRC_PATH)

        receiver_lambda = _lambda.Function(
            self,
            "receiver",
            code=code_asset,
            handler="receiver_handler.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
        )

        sender_lambda = _lambda.Function(
            self,
            "sender",
            code=code_asset,
            handler="sender_handler.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            on_failure=lambda_destinations.SnsDestination(fifo_topic),
            on_success=lambda_destinations.SqsDestination(fifo_queue)
        )

        invoke_success_payload = dict_to_json_to_b64_str({"return": "success"})
        invoke_failure_payload = dict_to_json_to_b64_str({"return": "failure"})

        CfnOutput(
            self,
            "invoke-success",
            value=f"aws lambda invoke --function-name {sender_lambda.function_name} --invocation-type Event --payload '{invoke_success_payload}' --no-cli-pager /dev/null"
        )

        CfnOutput(
            self,
            "invoke-failure",
            value=f"aws lambda invoke --function-name {sender_lambda.function_name} --invocation-type Event --payload '{invoke_failure_payload}' --no-cli-pager /dev/null"
        )
