import boto3
import logging
import time
import re

LOGGER = logging.getLogger("athena_helper")


class AthenaQuery:

    def __init__(self, query, database_name, result_bucket,
                 boto_session=None,
                 query_timeout=60,
                 query_execution_id=None):
        self._query = query
        self._database_name = database_name
        self._query_state = None
        self._state_change_reason = None
        self._stats_execution_time_in_millis = 0
        self._stats_data_scanned_in_bytes = 0
        self._query_execution_id = query_execution_id
        self._result_bucket = result_bucket
        self._query_timeout = query_timeout

        if boto_session is None:
            self._boto_session = boto3.Session()
        else:
            self._boto_session = boto_session

    @staticmethod
    def from_execution_id(execution_id, boto_session=None):
        """
        Returns an instance of AthenaQuery that represents the execution id.
        :param execution_id:
        :param boto_session: A configured instance of a boto Session (optional)
        :return: AthenaQuery
        """

        if boto_session is None:
            boto_session = boto3.Session()

        athena_client = boto_session.client("athena")

        query_information = athena_client.get_query_execution(
            QueryExecutionId=execution_id
        )

        query_execution = query_information["QueryExecution"]

        # Extract the relevant information to populate the AthenaQuery Object
        database_name = query_execution["QueryExecutionContext"]["Database"]
        query = query_execution["Query"]
        result_bucket = query_execution["ResultConfiguration"]["OutputLocation"]

        match = re.search(r'^(s3://.*?/)', result_bucket)
        if match:
            result_bucket = match.group(1)
        else:
            raise RuntimeError("Couldn't extract the s3-path from {}".format(result_bucket))

        # build the AthenaQuery object
        return AthenaQuery(
            query,
            database_name,
            result_bucket,
            boto_session=boto_session,
            query_execution_id=execution_id
        )

    def __str__(self):
        return "Query: {query} Database: {database} Bucket: {bucket}".format(
            query=self._query,
            database=self._database_name,
            bucket=self._result_bucket
        )

    def _update_query_status(self):
        """
        Updates the internal query status of this object.
        NOTE: this fails silently, if the query has not yet been executed!
        :return:
        """

        # TODO: We should probably do some kind of rate limiting here...

        if self._query_execution_id is None:
            # No execution yet
            LOGGER.debug("The query has not been executed!")
            return None

        client = self._boto_session.client('athena')

        query_status = client.get_query_execution(
            QueryExecutionId=self._query_execution_id
        )

        query_execution = query_status["QueryExecution"]

        self._query_state = query_execution["Status"]["State"]
        LOGGER.debug("Current Query State for Execution ID: %s is: %s", self._query_execution_id,  self._query_state)

        if "StateChangeReason" in query_execution["Status"]:
            self._state_change_reason = query_execution["Status"]["StateChangeReason"]
        else:
            # No state change?!?
            pass

        if "EngineExecutionTimeInMillis" in query_execution["Statistics"]:
            self._stats_execution_time_in_millis = query_execution["Statistics"]["EngineExecutionTimeInMillis"]
        else:
            self._stats_execution_time_in_millis = 0

        if "DataScannedInBytes" in query_execution["Statistics"]:
            self._stats_data_scanned_in_bytes = query_execution["Statistics"]["DataScannedInBytes"]
        else:
            self._stats_data_scanned_in_bytes = 0

    def get_status_information(self):
        self._update_query_status()

        return {
            "QueryState": self._query_state,
            "ExecutionTimeInMillis": self._stats_execution_time_in_millis,
            "StateChangeReason": self._state_change_reason,
            "DataScannedInBytes": self._stats_data_scanned_in_bytes
        }

    def execute(self):
        client = self._boto_session.client('athena')

        response = client.start_query_execution(
            QueryString=self._query,
            QueryExecutionContext={
                'Database': self._database_name
            },
            ResultConfiguration={
                'OutputLocation': self._result_bucket,
            }
        )

        LOGGER.debug("Scheduled Athena-Query - Query Execution Id: {}".format(response["QueryExecutionId"]))

        self._query_execution_id = response["QueryExecutionId"]
        return response["QueryExecutionId"]

    def wait_for_result(self, query_timeout_in_seconds=None):

        if query_timeout_in_seconds is None:
            query_timeout_in_seconds = self._query_timeout

        sleep_in_seconds = 1
        current_wait_time = 0
        while current_wait_time <= query_timeout_in_seconds:

            self._update_query_status()

            if self._query_state in ["SUCCEEDED"]:
                return None
            elif self._query_state in ["CANCELED", "FAILED"]:
                error_string = "Query Execution Failed, Id: {} - StateChangeReason {}".format(
                    self._query_execution_id,
                    self._state_change_reason
                )
                raise RuntimeError(error_string)
            else:
                # Either Queued or Running
                pass

            current_wait_time += sleep_in_seconds
            time.sleep(sleep_in_seconds)

        raise TimeoutError("The Athena query took longer than {} seconds to run! (It's still running)".format(
            query_timeout_in_seconds))

    def get_result(self):
        if self._query_execution_id is None:
            raise RuntimeError("This query hasn't yet been executed, can't retrieve the result!")

        # Wait until the query has been successfully executed
        self.wait_for_result()

        client = self._boto_session.client('athena')

        # Return the result
        return client.get_query_results(
            QueryExecutionId=self._query_execution_id
        )
