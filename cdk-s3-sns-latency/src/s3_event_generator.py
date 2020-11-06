import logging
import os

import boto3

ENV_BUCKET_WITH_LAMBDA = "BUCKET_WITH_LAMBDA"
ENV_BUCKET_WITH_SNS = "BUCKET_WITH_SNS"

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

def lambda_handler(event: dict, context: dict):
    buckets = [
        os.environ[ENV_BUCKET_WITH_LAMBDA],
        os.environ[ENV_BUCKET_WITH_SNS]
    ]

    num_of_objects_per_bucket = event.get("objectCount", 1000)

    s3_resource = boto3.resource("s3")

    for bucket_name in buckets:

        for file_count in range(num_of_objects_per_bucket):
            file_name = f"object_{file_count}"

            LOGGER.debug("Creating object %s in bucket %s", file_name, bucket_name)

            s3_object = s3_resource.Object(
                bucket_name=bucket_name,
                key=file_name
            )

            # Upload the data
            s3_object.put(
                Body="Some String"
            )
