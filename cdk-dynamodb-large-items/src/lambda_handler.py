import collections
import csv
import io
import json
import logging
import os
import random
import statistics
import time

from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

MEMORY_SIZE = str(os.environ.get("MEMORY_SIZE", "N/A"))
TABLE_NAME = os.environ.get("TABLE_NAME", "N/A")
INVOKER_TOPIC_ARN = os.environ.get("INVOKER_TOPIC_ARN", "N/A")

# The item sizes we try to read from the table
ITEM_SIZES_IN_KB = [4, 64, 128, 256, 400]

FLAT_JSON_PATH = os.path.join(os.path.dirname(__file__), "flat_400kb_item.json")
NESTED_JSON_PATH = os.path.join(os.path.dirname(__file__), "nested_400kb_item.json")

def record_measurement_result(memory_size: str, test_method: str, item_size: str, time_in_millis: int):
    
    LOGGER.debug(
        "Recording result for a %s call with memory size %s that took %s ms",
        test_method,
        memory_size,
        time_in_millis
    )

    update_expression = "SET #item_size = list_append(if_not_exists(#item_size, :empty_list), :measurements)" \
        + ", #tm = :tm, #ms = :ms"

    expression_attribute_names = {
        "#tm": "testMethod",
        "#ms": "memorySize",
        "#item_size": item_size,
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

    item_keys = []
    for size in ITEM_SIZES_IN_KB:
        item_keys.append(f"{size}KB_FLAT")
        item_keys.append(f"{size}KB_NESTED")
    
    for item in query_result["Items"]:

        memory_size = item["memorySize"]
        test_method = item["testMethod"]
        
        result_dict[memory_size]["memorySize"] = memory_size

        if test_method == "deserialize":
            # Special case for just the parsing
            
            flat_values = item["DESERIALIZED_FLAT"]
            avg_flat_value = int(statistics.mean([int(i) for i in flat_values]))
            result_dict[memory_size]["DESERIALIZE_FLAT"] = avg_flat_value

            nested_values = item["DESERIALIZED_NESTED"]
            avg_nested_value = int(statistics.mean([int(i) for i in nested_values]))
            result_dict[memory_size]["DESERIALIZE_NESTED"] = avg_nested_value

        else:

            for key in item_keys:
                values = item[key]

                avg_value = int(statistics.mean([int(i) for i in values]))

                result_dict[memory_size][f"{key}_{test_method[:1].upper()}"] = avg_value

    
    field_names = ["memorySize"]
    for key in item_keys:
        field_names.append(f"{key}_C")
        field_names.append(f"{key}_R")

    field_names.append("DESERIALIZE_FLAT")
    field_names.append("DESERIALIZE_NESTED")

    mem_file = io.StringIO()
    writer = csv.DictWriter(
        mem_file,
        fieldnames=field_names,
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
    
    ddb = boto3.client("dynamodb")

    # Get a sample item to make sure the connection to DynamoDB is already established.
    ddb.get_item(TableName=TABLE_NAME, Key={"PK": {"S": "ITEM"}, "SK": {"S": "META"}})

    for size in ITEM_SIZES_IN_KB:

        # flat

        pk = "ITEM"
        sk = f"{str(size).zfill(3)}KB_FLAT"

        started_at = datetime.now()

        response = ddb.get_item(
            Key={
                "PK": {"S": pk},
                "SK": {"S": sk}
            },
            TableName=TABLE_NAME,
            ReturnConsumedCapacity="TOTAL"
        )

        finished_at = datetime.now()
        capacity_units = response["ConsumedCapacity"]["CapacityUnits"]

        time_it_took_in_millis = int((finished_at - started_at).total_seconds() * 1000)

        print(f"Read the {size}KB flat item in {time_it_took_in_millis}ms and consumed {capacity_units} capacity units.")

        record_measurement_result(
            memory_size=MEMORY_SIZE,
            item_size=f"{size}KB_FLAT",
            test_method="client",
            time_in_millis=time_it_took_in_millis
        )

        # nested

        pk = "ITEM"
        sk = f"{str(size).zfill(3)}KB_NESTED"

        started_at = datetime.now()

        response = ddb.get_item(
            Key={
                "PK": {"S": pk},
                "SK": {"S": sk}
            },
            TableName=TABLE_NAME,
            ReturnConsumedCapacity="TOTAL"
        )

        finished_at = datetime.now()
        capacity_units = response["ConsumedCapacity"]["CapacityUnits"]

        time_it_took_in_millis = int((finished_at - started_at).total_seconds() * 1000)

        print(f"Read the {size}KB nested item in {time_it_took_in_millis}ms and consumed {capacity_units} capacity units.")

        record_measurement_result(
            memory_size=MEMORY_SIZE,
            item_size=f"{size}KB_NESTED",
            test_method="client",
            time_in_millis=time_it_took_in_millis
        )

def resource_handler(event: dict, context):

    # Measurements for pure json data
    with open(FLAT_JSON_PATH) as flat_file, open(NESTED_JSON_PATH) as nested_file:
        flat_file_content = flat_file.read()
        nested_file_content = nested_file.read()
    
        started_at = datetime.now()
        deserialized = json.loads(flat_file_content)

        finished_at = datetime.now()

        time_it_took_in_millis = int((finished_at - started_at).total_seconds() * 1000)

        print(f"Deserialized the 400KB flat item in {time_it_took_in_millis}ms from disk.")

        record_measurement_result(
            memory_size=MEMORY_SIZE,
            item_size=f"DESERIALIZED_FLAT",
            test_method="deserialize",
            time_in_millis=time_it_took_in_millis
        )

        started_at = datetime.now()
        deserialized = json.loads(nested_file_content)

        finished_at = datetime.now()

        time_it_took_in_millis = int((finished_at - started_at).total_seconds() * 1000)

        print(f"Deserialized the 400KB nested item in {time_it_took_in_millis}ms from disk.")

        record_measurement_result(
            memory_size=MEMORY_SIZE,
            item_size=f"DESERIALIZED_NESTED",
            test_method="deserialize",
            time_in_millis=time_it_took_in_millis
        )


    table = boto3.resource("dynamodb").Table(TABLE_NAME)

    # Get a sample item to make sure the connection to DynamoDB is already established.
    table.get_item(Key={"PK": "ITEM", "SK": "META"})

    for size in ITEM_SIZES_IN_KB:

        # flat

        pk = "ITEM"
        sk = f"{str(size).zfill(3)}KB_FLAT"

        started_at = datetime.now()

        response = table.get_item(
            Key={
                "PK": pk,
                "SK": sk
            },
            ReturnConsumedCapacity="TOTAL"
        )

        finished_at = datetime.now()
        capacity_units = response["ConsumedCapacity"]["CapacityUnits"]

        time_it_took_in_millis = int((finished_at - started_at).total_seconds() * 1000)

        print(f"Read the {size}KB flat item in {time_it_took_in_millis}ms and consumed {capacity_units} capacity units.")

        record_measurement_result(
            memory_size=MEMORY_SIZE,
            item_size=f"{size}KB_FLAT",
            test_method="resource",
            time_in_millis=time_it_took_in_millis
        )

        # nested

        pk = "ITEM"
        sk = f"{str(size).zfill(3)}KB_NESTED"

        started_at = datetime.now()

        response = table.get_item(
            Key={
                "PK": pk,
                "SK": sk
            },
            ReturnConsumedCapacity="TOTAL"
        )

        finished_at = datetime.now()
        capacity_units = response["ConsumedCapacity"]["CapacityUnits"]

        time_it_took_in_millis = int((finished_at - started_at).total_seconds() * 1000)

        print(f"Read the {size}KB nested item in {time_it_took_in_millis}ms and consumed {capacity_units} capacity units.")

        record_measurement_result(
            memory_size=MEMORY_SIZE,
            item_size=f"{size}KB_NESTED",
            test_method="resource",
            time_in_millis=time_it_took_in_millis
        )

def create_flat_item_of_size(size_in_kb: int) -> dict:
    # based on calculations here: https://zaccharles.github.io/dynamodb-calculator/

    if size_in_kb not in range(1, 401):
        raise ValueError("Item size has to be between 1 and 400 KB")

    template = {
        "PK": {
            "S": "ITEM"
        },
        "SK": {
            "S": "000KB_FLAT"
        },
        "payload": {
            "S": ""
        }
    } # This is 25 bytes
    template["SK"]["S"] = f"{str(size_in_kb).zfill(3)}KB_FLAT"
    payload = "X" * (1024 * size_in_kb - 25)
    template["payload"]["S"] = payload
    return template

def create_nested_item_of_size(size_in_kb: int) -> dict:
    # based on calculations here: https://zaccharles.github.io/dynamodb-calculator/

    if size_in_kb not in range(1, 401):
        raise ValueError("Item size has to be between 1 and 400 KB")

    template = {
        "PK": {
            "S": "ITEM"
        },
        "SK": {
            "S": "000KB_NESTED"
        },
        "payload": {
            "L": []
        }
    } # This is 30 bytes

    list_item = {
        "M": {
            "time": {
                "S": "1614712316"
            },
            "action": {
                "S": "list"
            },
            "id": {
                "S": "123"
            }
        }
    }  # 36 bytes

    number_of_items = int((1024 * size_in_kb - 30) / 36)

    template["SK"]["S"] = f"{str(size_in_kb).zfill(3)}KB_NESTED"
    for _ in range(number_of_items):
        template["payload"]["L"].append(list_item)
    return template

def create_sample_items():

    ddb_client = boto3.client("dynamodb")

    for size in ITEM_SIZES_IN_KB:
        item = create_flat_item_of_size(size)
    
        ddb_client.put_item(
            TableName=TABLE_NAME,
            Item=item
        )

        item = create_nested_item_of_size(size)
    
        ddb_client.put_item(
            TableName=TABLE_NAME,
            Item=item
        )
    
    # Item to query before the actual tests to make sure a connection is already established.
    meta_item = {
        "PK": {
            "S": "ITEM"
        },
        "SK": {
            "S": "META"
        }
    }

    ddb_client.put_item(
        TableName=TABLE_NAME,
        Item=meta_item
    )
    

def invoke_handler(event: dict, context):

    sns_topic = boto3.resource("sns").Topic(INVOKER_TOPIC_ARN)

    create_sample_items()

    n = int(event.get("n", 100))

    for _ in range(n):
        sns_topic.publish(Message="Go for it.")
        time.sleep(random.randint(1,5))