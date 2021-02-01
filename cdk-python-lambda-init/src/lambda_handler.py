import collections
import csv
import io
import logging
import os
import random
import statistics

from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

MEMORY_SIZE = str(os.environ.get("MEMORY_SIZE", "N/A"))
TABLE_NAME = os.environ.get("TABLE_NAME", "N/A")
INVOKER_TOPIC_ARN = os.environ.get("INVOKER_TOPIC_ARN", "N/A")

COLD_START = True

def record_measurement_result(memory_size: str, test_method: str, time_in_millis: int):
    
    LOGGER.debug(
        "Recording result for a %s call with memory size %s that took %s ms",
        test_method,
        memory_size,
        time_in_millis
    )

    update_expression = "SET #measures = list_append(if_not_exists(#measures, :empty_list), :measurements)" \
        + ", #tm = :tm, #ms = :ms"

    expression_attribute_names = {
        "#measures": "measurements",
        "#tm": "testMethod",
        "#ms": "memorySize",
    }

    expression_attribute_values = {
        ":empty_list": [],
        ":measurements": [time_in_millis],
        ":tm": test_method,
        ":ms": memory_size
    }

    dynamodb = boto3.resource("dynamodb")
    result_table = dynamodb.Table(TABLE_NAME)

    result_table.update_item(
        Key={
            "PK": "MEASUREMENT",
            "SK": f"METHOD#{test_method}#MEMORY#{memory_size}"
        },
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values
    )


def result_aggregator(event: dict, context):

    dynamodb = boto3.resource("dynamodb")
    result_table = dynamodb.Table(TABLE_NAME)

    query_result = result_table.query(
        KeyConditionExpression=Key("PK").eq("MEASUREMENT")
    )

    result_dict = collections.defaultdict(dict)
    
    for item in query_result["Items"]:

        memory_size = item["memorySize"]
        test_method = item["testMethod"]

        avg_value = int(statistics.mean([int(i) for i in item["measurements"]]))
        
        result_dict[memory_size][test_method] = avg_value
        result_dict[memory_size]["memorySize"] = memory_size
    
    mem_file = io.StringIO()
    writer = csv.DictWriter(
        mem_file,
        fieldnames=["memorySize", "client", "resource"],
        delimiter=";",
    )
    
    writer.writeheader()
    for value in result_dict.values():
        writer.writerow(value)
    
    print(mem_file.getvalue())
    return {"csvContent": mem_file.getvalue()}

def self_mutate(function_name: str):
    """
    Adds / updates the ELEMENT_OF_SURPRISE environment variable on this function.
    This results in old execution contexts being discarded for future events.
    """
    
    lambda_client = boto3.client("lambda")
    function_config = lambda_client.get_function_configuration(
        FunctionName=function_name
    )

    existing_env = function_config["Environment"]["Variables"]
    existing_env["ELEMENT_OF_SURPRISE"] = str(random.randint(1, 100_000))

    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Environment={"Variables": existing_env}
    )

def client_handler(event: dict, context):

    global COLD_START

    if not COLD_START:
        self_mutate(context.function_name)
        raise RuntimeError("Boto3 is already cached, this would ruin the measurements!")

    COLD_START = False
    
    started_at = datetime.now()
    boto3.client("dynamodb")
    finished_at = datetime.now()

    time_it_took_in_millis = int((finished_at - started_at).total_seconds() * 1000)

    record_measurement_result(
        memory_size=MEMORY_SIZE,
        test_method="client",
        time_in_millis=time_it_took_in_millis
    )

    # Update the function to clear up existing execution contexts
    self_mutate(context.function_name)

def resource_handler(event: dict, context):

    global COLD_START

    if not COLD_START:
        self_mutate(context.function_name)
        raise RuntimeError("Boto3 is already cached, this would ruin the measurements!")

    COLD_START = False
    
    started_at = datetime.now()
    boto3.resource("dynamodb")
    finished_at = datetime.now()

    time_it_took_in_millis = int((finished_at - started_at).total_seconds() * 1000)

    record_measurement_result(
        memory_size=MEMORY_SIZE,
        test_method="resource",
        time_in_millis=time_it_took_in_millis
    )

    # Update the function to clear up existing execution contexts
    self_mutate(context.function_name)

def invoke_handler(event: dict, context):

    sns_topic = boto3.resource("sns").Topic(INVOKER_TOPIC_ARN)

    n = int(event.get("n", 100))

    for _ in range(n):
        sns_topic.publish(Message="Go for it.")