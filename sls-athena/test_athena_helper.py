from athena_helper import AthenaQuery
import boto3
import logging

# We can only really do an integration test of this

LOGGER = logging.getLogger()


def set_up_logging():
    global LOGGER

    output_handler = logging.StreamHandler()
    output_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    output_handler.setFormatter(formatter)
    LOGGER.addHandler(output_handler)
    LOGGER.setLevel(logging.DEBUG)

    # SILENCE!
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def main():

    set_up_logging()

    LOGGER.debug("Begin test")

    boto_session = boto3.Session()

    # This is the default table
    query = "select * from elb_logs limit 1"
    database_name = "sampledb"

    # Build the name of the default Athena bucket
    account_id = boto_session.client('sts').get_caller_identity().get('Account')
    region = boto_session.region_name
    result_bucket = "s3://aws-athena-query-results-{}-{}/".format(account_id, region)

    LOGGER.info("Creating the Athena Query Object")
    my_query = AthenaQuery(query, database_name, result_bucket)

    LOGGER.info("Beginning query execution")
    query_execution_id = my_query.execute()

    LOGGER.info("Retrieving query results")
    # This will automatically wait for the query to execute
    query_results = my_query.get_result()

    LOGGER.info("Constructing a new AthenaQuery object from the existing execution id")
    aq = AthenaQuery.from_execution_id(query_execution_id)

    LOGGER.info("Retrieving status information from the new object")
    aq.get_status_information()


if __name__ == "__main__":
    main()
