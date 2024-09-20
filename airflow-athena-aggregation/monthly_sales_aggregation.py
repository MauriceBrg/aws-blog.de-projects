# pylint: disable=W0104
import fnmatch
import logging
from datetime import timedelta, datetime

import textwrap
from airflow.decorators import task
from airflow.exceptions import AirflowException
from airflow.models.dag import DAG
from airflow.models.param import Param
from airflow.providers.amazon.aws.operators.athena import AthenaOperator
from airflow.providers.amazon.aws.operators.s3 import S3DeleteObjectsOperator


LOGGER = logging.getLogger(__name__)

DATASET_START = datetime.fromisoformat("1992-01-01")
DATASET_END = datetime.fromisoformat("1998-08-02")


INSERT_INTO_SQL = textwrap.dedent(
    """
    /*
    Monthly sales per market segment, nation, and region
    */

    insert into {table_name} (
        c_mktsegment,
        n_name,
        n_nationkey,
        r_name,
        r_regionkey,
        total_revenue,
        "year",
        "month"
    )
    select c_mktsegment,
        n_name,
        n_nationkey,
        r_name,
        r_regionkey,
        sum(o_totalprice) as total_revenue,
        year(o_orderdate) as "year",
        month(o_orderdate) as "month"
    from customer c
        join orders o on c.c_custkey = o.o_custkey
        join nation n on c_nationkey = n.n_nationkey
        join region r on r_regionkey = n.n_regionkey
    where year(o_orderdate) = year(date('{date}'))
      and month(o_orderdate) = month(date('{date}'))
    group by c_mktsegment,
        n_name,
        n_nationkey,
        r_name,
        r_regionkey,
        year(o_orderdate),
        month(o_orderdate)
        ;
    """
)

CREATE_TABLE_SQL = textwrap.dedent(
    """
    create external table if not exists {table_name} (
        c_mktsegment STRING,
        n_name STRING,
        n_nationkey INT,
        r_name STRING,
        r_regionkey INT,
        total_revenue DECIMAL(38, 2)
    )
    partitioned by (year BIGINT, month BIGINT)
    stored as parquet
    location 's3://{bucket_name}/{prefix}/{table_name}'
    """
)


@task.branch(
    task_id="handle_result",
    task_display_name="Table doesn't exist?",
    trigger_rule="all_failed",
)
def is_table_missing(**context):

    error_message = context["task_instance"].xcom_pull(
        key="insert_error", task_ids="insert_into_aggregate_table"
    )

    if fnmatch.fnmatch(error_message, "*Error: Table * not found in database*"):
        LOGGER.info("Table doesn't exist, next step: create table.")
        return "create_aggregate_table"

    raise AirflowException(f"Unknown error during insert {error_message}")


with DAG(
    dag_id="monthly_sales_aggregation",
    dag_display_name="Monthly Sales Aggregation",
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    start_date=DATASET_START,
    end_date=DATASET_END,
    schedule_interval="@monthly",
    catchup=False,
    params={
        "s3_bucket": Param(
            default="athena-mb-test",
            description="Bucket to store the data in.",
            type="string",
            title="S3 Bucket",
        ),
        "s3_prefix": Param(
            default="aggregation/",
            description="Prefix to store the data under. Must be either / (root of bucket) or a string ending in slash, e.g. some/prefix/",
            type="string",
            title="S3 Prefix",
            pattern=r"(^\/$|^[^\/].*\/$)",
        ),
        "database_name": Param(
            default="tpch100gb",
            description="Name of the Glue Database to store the tables in. Will be created if it doesn't exist.",
            type="string",
        ),
        "monthly_sales_table_name": Param(
            default="monthly_sales",
            description="Name to be used for the daily sales table.",
            type="string",
        ),
        "athena_workgroup": Param(
            default="primary",
            type="string",
            description="Name of the Athena Workgroup to use.",
        ),
        "athena_output_location_s3_uri": Param(
            default="s3://mb-demo-bucket-2020/athena-temp/",
            type="string",
            pattern=r"^s3:\/\/[a-z0-9-_]*\/.*$",
            title="Athena Result location",
            description="S3 URI to store the Athena results under, e.g. s3://my-bucket/and_prefix/.",
        ),
    },
) as dag:

    insert_params = dict(
        query=INSERT_INTO_SQL.format(
            table_name="{{params.monthly_sales_table_name}}",
            date="{{ds}}",
        ),
        database="{{params.database_name}}",
        workgroup="{{params.athena_workgroup}}",
        output_location="{{params.athena_output_location_s3_uri}}",
        retries=0,
    )

    def _add_exception_to_xcom(context):
        context["task_instance"].xcom_push("insert_error", str(context["exception"]))

    insert_into_aggregate_table = AthenaOperator(
        task_id="insert_into_aggregate_table",
        task_display_name="Insert into Monthly Sales",
        on_failure_callback=_add_exception_to_xcom,
        **insert_params,
    )

    clean_s3_prefix = S3DeleteObjectsOperator(
        task_id="clean_s3_prefix",
        task_display_name="Delete Existing data from S3",
        bucket="{{params.s3_bucket}}",
        prefix="{{params.s3_prefix}}{{params.monthly_sales_table_name}}/{{ macros.ds_format(ds, '%Y-%m-%d', 'year=%Y/month=%-m/') }}",
    )

    clean_s3_prefix >> insert_into_aggregate_table

    handle_missing_table = is_table_missing()
    insert_into_aggregate_table >> handle_missing_table

    create_aggregate_table = AthenaOperator(
        task_id="create_aggregate_table",
        task_display_name="Create the Monthly Sales Table.",
        query=CREATE_TABLE_SQL.format(
            table_name="{{params.monthly_sales_table_name}}",
            bucket_name="{{params.s3_bucket}}",
            prefix="{{params.s3_prefix}}",
        ),
        database="{{params.database_name}}",
        workgroup="{{params.athena_workgroup}}",
        output_location="{{params.athena_output_location_s3_uri}}",
    )

    handle_missing_table >> create_aggregate_table

    insert_again = AthenaOperator(
        task_id="insert_again",
        task_display_name="Insert (again) into Monthly Sales",
        **insert_params,
    )

    create_aggregate_table >> insert_again

if __name__ == "__main__":
    dag.test()
