import logging
import statistics
import typing

import boto3
import click

from boto3.dynamodb.conditions import Key

import cdk_s3_sns_latency.cdk_s3_sns_latency_stack as stack

BUCKET_WITH_LAMBDA: str = None
BUCKET_WITH_SNS: str = None
MEASUREMENT_TABLE_NAME: str = None
GENERATOR_FUNCTION_NAME: str = None


def get_consistent_snapshot(table_name) -> typing.List[dict]:
    """
    Takes a consistent snapshot of the order book table and return the dictionary representation.
    :return: dict of Order Summary representations
    """

    dynamo_db = boto3.resource("dynamodb")
    order_book_table = dynamo_db.Table(table_name)

    # This just wraps the internal iterable based  method for compatibility.
    return list(_get_consistent_snapshot(order_book_table))


def _get_consistent_snapshot(
        dynamodb_table: boto3.resources.base.ServiceResource,
        _last_evaluated_key: dict = None
    ) -> typing.Iterable[dict]:

    query_arguments = {
    }

    if _last_evaluated_key is not None:
        # This means we're paginating and have to add the start offset.
        query_arguments["ExclusiveStartKey"] = _last_evaluated_key

    scan_result = dynamodb_table.scan(**query_arguments)

    for item in scan_result["Items"]:
        yield item

    if "LastEvaluatedKey" in scan_result:
        # This means there's another page and we need to paginate
        yield from _get_consistent_snapshot(dynamodb_table, scan_result["LastEvaluatedKey"])

def get_params():
    """Get the information about the environment and store it in the global variables..."""
    ssm_client = boto3.client("ssm")

    global BUCKET_WITH_LAMBDA, BUCKET_WITH_SNS, MEASUREMENT_TABLE_NAME, GENERATOR_FUNCTION_NAME

    click.secho("Loading environment information...", fg="yellow")

    BUCKET_WITH_LAMBDA = ssm_client.get_parameter(Name=stack.BUCKET_WITH_LAMBDA_PARAMETER)["Parameter"]["Value"]
    BUCKET_WITH_SNS = ssm_client.get_parameter(Name=stack.BUCKET_WITH_SNS_PARAMETER)["Parameter"]["Value"]
    MEASUREMENT_TABLE_NAME = ssm_client.get_parameter(Name=stack.MEASUREMENT_TABLE_PARAMETER)["Parameter"]["Value"]
    GENERATOR_FUNCTION_NAME = ssm_client.get_parameter(Name=stack.GENERATOR_FUNCTION_NAME_PARAMETER)["Parameter"]["Value"]

    click.secho("Done.", fg="yellow")

@click.group()
def cli():
    pass

@cli.command()
@click.argument("number_of_measurements", default=100)
def start(number_of_measurements):
    get_params()

    lambda_client = boto3.client("lambda")

    click.secho(f"Invoking the function to create {number_of_measurements} objects... this might take a while.", fg="yellow")

    lambda_client.invoke(
        FunctionName=GENERATOR_FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload='{"objectCount": ' + str(number_of_measurements) + '}'
    )

    click.secho("Done.", fg="green")

@cli.command()
def summary():
    get_params()

    table = boto3.resource("dynamodb").Table(MEASUREMENT_TABLE_NAME)
    
    for bucket_name in [BUCKET_WITH_LAMBDA, BUCKET_WITH_SNS]:

        s3_to_lambda_latencies = []
        s3_to_sns_latencies = []
        sns_to_lambda_latencies = []

        click.secho(f"Exporting values for bucket {bucket_name}", fg="yellow")

        response = table.query(KeyConditionExpression=Key("PK").eq(bucket_name))

        click.secho(f"Got {response['Count']} values...")

        for item in response["Items"]:
            s3_to_lambda_latencies.append(int(item["s3ToLambdaMS"]))
            s3_to_sns_latencies.append(int(item["s3ToSnsMS"]))
            sns_to_lambda_latencies.append(int(item["snsToLambdaMS"]))

        click.secho(f"[S3 -> Lambda] Mean latency for {bucket_name}: {statistics.mean(s3_to_lambda_latencies)}")
        click.secho(f"[S3 -> Lambda] Min latency for {bucket_name}: {min(s3_to_lambda_latencies)}")
        click.secho(f"[S3 -> Lambda] Max latency for {bucket_name}: {max(s3_to_lambda_latencies)}")
        click.secho(f"[S3 -> SNS] Mean latency for {bucket_name}: {statistics.mean(s3_to_sns_latencies)}")
        click.secho(f"[S3 -> SNS] Min latency for {bucket_name}: {min(s3_to_sns_latencies)}")
        click.secho(f"[S3 -> SNS] Max latency for {bucket_name}: {max(s3_to_sns_latencies)}")
        click.secho(f"[SNS -> Lambda] Mean latency for {bucket_name}: {statistics.mean(sns_to_lambda_latencies)}")
        click.secho(f"[SNS -> Lambda] Min latency for {bucket_name}: {min(sns_to_lambda_latencies)}")
        click.secho(f"[SNS -> Lambda] Max latency for {bucket_name}: {max(sns_to_lambda_latencies)}")

@cli.command()
def clear():

    get_params()
    
    items = get_consistent_snapshot(MEASUREMENT_TABLE_NAME)

    click.confirm(f"Are you sure you want to delete {len(items)} items from table {MEASUREMENT_TABLE_NAME}?", abort=True)

    ddb_resource = boto3.resource("dynamodb")
    table = ddb_resource.Table(MEASUREMENT_TABLE_NAME)

    keys = [ item["AttributeName"] for item in table.key_schema ]

    click.echo(f'Got keys: {", ".join(keys)}')
    
    with click.progressbar(items, label="Deleting Items...") as delete_list, table.batch_writer() as batch:

        for item in delete_list:
            
            key_dict = {key_item: item[key_item] for key_item in keys}

            batch.delete_item(
                Key=key_dict
            )
    
    s3 = boto3.resource("s3")

    for bucket_name in [BUCKET_WITH_SNS, BUCKET_WITH_LAMBDA]:
        click.secho(f"Clearing Bucket {bucket_name}")

        bucket = s3.Bucket(bucket_name)

        delete_count = 0

        for s3_object in bucket.objects.all():
            s3_object.delete()
            delete_count += 1
        
        click.secho(f"Deleted {delete_count} objects from {bucket_name}")

if __name__ == "__main__":
    cli()