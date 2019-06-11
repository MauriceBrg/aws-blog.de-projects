import boto3
from athena_helper import AthenaQuery

BOTO_SESSION = boto3.Session()


def start_long_running_query(event, context):

    # This is the default table
    query = "select * from elb_logs limit 1"
    database_name = "sampledb"

    # Build the name of the default Athena bucket
    account_id = BOTO_SESSION.client('sts').get_caller_identity().get('Account')
    region = BOTO_SESSION.region_name
    result_bucket = "s3://aws-athena-query-results-{}-{}/".format(account_id, region)

    my_query = AthenaQuery(query, database_name, result_bucket)

    query_execution_id = my_query.execute()

    # This will be processed by our waiting-step
    event = {
        "MyQueryExecutionId": query_execution_id,
        "WaitTask": {
            "QueryExecutionId": query_execution_id,
            "ResultPrefix": "Sample"
        }
    }

    return event


def get_long_running_query_status(event, context):

    query_execution_id = event["WaitTask"]["QueryExecutionId"]
    aq = AthenaQuery.from_execution_id(query_execution_id)

    status_information = aq.get_status_information()
    event["WaitTask"]["QueryState"] = status_information["QueryState"]

    status_key = "{}StatusInformation".format(event["WaitTask"]["ResultPrefix"])
    event[status_key] = status_information

    return event


def get_long_running_result(event, context):
    query_execution_id = event["MyQueryExecutionId"]

    # Build the query object from the execution id
    aq = AthenaQuery.from_execution_id(query_execution_id)

    # Fetch the result
    result_data = aq.get_result()

    # Do whatever you want with the result

    event["GotResult"] = True
    return event


def short_running_query(event, context):

    # This is the default table
    query = "select elb_name from elb_logs limit 1"
    database_name = "sampledb"

    # Build the name of the default Athena bucket
    account_id = BOTO_SESSION.client('sts').get_caller_identity().get('Account')
    region = BOTO_SESSION.region_name
    result_bucket = "s3://aws-athena-query-results-{}-{}/".format(account_id, region)

    my_query = AthenaQuery(query, database_name, result_bucket)

    my_query.execute()
    result_data = my_query.get_result()

    # Process the result

    return result_data
