import json
import logging
import os

from datetime import datetime, timezone

import boto3

ENV_MEASUREMENT_TABLE = "MEASUREMENT_TABLE"

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

TABLE_RESOURCE = boto3.resource("dynamodb").Table(os.environ[ENV_MEASUREMENT_TABLE])

def str_to_datetime(input_string):
    return datetime.strptime(input_string, '%Y-%m-%dT%H:%M:%S.%f%z')

def lambda_handler(event: dict, context: dict):

    function_start_timestamp = datetime.now(timezone.utc)
    
    for event_record in event["Records"]:

        if event_record.get("EventSource") == "aws:sns":
            # Handle SNS event
            sns_timestamp = event_record["Sns"]["Timestamp"]
            s3_events = json.loads(event_record["Sns"]["Message"])["Records"]
            
            for s3_event in s3_events:
                # Handle the wrapped s3-event
                s3_timestamp = s3_event["eventTime"]
                bucket_name = s3_event["s3"]["bucket"]["name"]
                object_key = s3_event["s3"]["object"]["key"]
                LOGGER.debug("Processing event for object %s in bucket %s", object_key, bucket_name)

                s3_to_lambda_milliseconds = int(
                    (function_start_timestamp - str_to_datetime(s3_timestamp)).total_seconds() * 1000
                )

                s3_to_sns_milliseconds = int(
                    (str_to_datetime(sns_timestamp) - str_to_datetime(s3_timestamp)).total_seconds() * 1000
                )

                sns_to_lambda_milliseconds = int(
                    (function_start_timestamp - str_to_datetime(sns_timestamp)).total_seconds() * 1000
                )

                measurement = {
                    "PK": bucket_name,
                    "SK": object_key,
                    "s3ToLambdaMS": s3_to_lambda_milliseconds,
                    "s3ToSnsMS": s3_to_sns_milliseconds,
                    "snsToLambdaMS": sns_to_lambda_milliseconds,
                    "s3Timestamp": s3_timestamp,
                    "snsTimestamp": sns_timestamp,
                    "lambdaTimestamp": function_start_timestamp.isoformat()
                }

                LOGGER.debug("S3 -> Lambda: %s", s3_to_lambda_milliseconds)
                LOGGER.debug("S3 -> SNS: %s", s3_to_sns_milliseconds)
                LOGGER.debug("SNS -> Lambda: %s", sns_to_lambda_milliseconds)

                TABLE_RESOURCE.put_item(
                    Item=measurement
                )

        elif event_record.get("eventSource") == "aws:s3":
            # Handle S3 event
            s3_timestamp = event_record["eventTime"]
            bucket_name = event_record["s3"]["bucket"]["name"]
            object_key = event_record["s3"]["object"]["key"]
            LOGGER.debug("Processing event for object %s in bucket %s", object_key, bucket_name)

            s3_to_lambda_milliseconds = int(
                (function_start_timestamp - str_to_datetime(s3_timestamp)).total_seconds() * 1000
            )

            measurement = {
                "PK": bucket_name,
                "SK": object_key,
                "s3ToLambdaMS": s3_to_lambda_milliseconds,
                "s3ToSnsMS": -1,
                "snsToLambdaMS": -1,
                "s3Timestamp": s3_timestamp,
                "snsTimestamp": "N/A",
                "lambdaTimestamp": function_start_timestamp.isoformat()
            }

            LOGGER.debug("S3 -> Lambda: %s", s3_to_lambda_milliseconds)

            TABLE_RESOURCE.put_item(
                Item=measurement
            )