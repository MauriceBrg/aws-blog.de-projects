import logging
from datetime import timedelta

import textwrap
from airflow.decorators import task
from airflow.models.dag import DAG
from airflow.models.param import Param
from airflow.operators.empty import EmptyOperator
from airflow.providers.amazon.aws.operators.athena import AthenaOperator
from airflow.utils.task_group import TaskGroup


LOGGER = logging.getLogger(__name__)

SOURCE_S3_BUCKET = "redshift-downloads"

TABLE_NAMES = [
    "region",
    "nation",
    "lineitem",
    "orders",
    "part",
    "supplier",
    "partsupp",
    "customer",
]

TABLE_NAME_TO_SQL_TEMPLATE: dict[str, str] = {
    "customer": """
CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (
  c_custkey BIGINT,
  c_name STRING,
  c_address STRING,
  c_nationkey INT,
  c_phone STRING,
  c_acctbal DECIMAL(12,2),
  c_mktsegment STRING,
  c_comment STRING
)
{suffix}
""",
    "lineitem": """
CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (
  l_orderkey BIGINT,
  l_partkey BIGINT,
  l_suppkey INT,
  l_linenumber INT,
  l_quantity DECIMAL(12,2),
  l_extendedprice DECIMAL(12,2),
  l_discount DECIMAL(12,2),
  l_tax DECIMAL(12,2),
  l_returnflag STRING,
  l_linestatus STRING,
  l_shipdate DATE,
  l_commitdate DATE,
  l_receiptdate DATE,
  l_shipinstruct STRING,
  l_shipmode STRING,
  l_comment STRING
)
{suffix}
""",
    "nation": """
CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (
  n_nationkey INT,
  n_name STRING,
  n_regionkey INT,
  n_comment STRING
)
{suffix}
""",
    "orders": """
CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (
  o_orderkey BIGINT,
  o_custkey BIGINT,
  o_orderstatus STRING,
  o_totalprice DECIMAL(12,2),
  o_orderdate DATE,
  o_orderpriority STRING,
  o_clerk STRING,
  o_shippriority INT,
  o_comment STRING
)
{suffix}
""",
    "part": """
CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (
  p_partkey BIGINT,
  p_name STRING,
  p_mfgr STRING,
  p_brand STRING,
  p_type STRING,
  p_size INT,
  p_container STRING,
  p_retailprice DECIMAL(12,2),
  p_comment STRING
)
{suffix}
""",
    "partsupp": """
CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (
  ps_partkey BIGINT,
  ps_suppkey INT,
  ps_availqty INT,
  ps_supplycost DECIMAL(12,2),
  ps_comment STRING
)
{suffix}
""",
    "region": """
CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (
  r_regionkey INT,
  r_name STRING,
  r_comment STRING
)
{suffix}
""",
    "supplier": """
CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (
  s_suppkey INT,
  s_name STRING,
  s_address STRING,
  s_nationkey INT,
  s_phone STRING,
  s_acctbal DECIMAL(12,2),
  s_comment STRING
)
{suffix}
""",
}


TABLE_TO_OPT_WITH_AND_SELECT: dict[str, tuple[str, str]] = {
    "orders": (
        ", partitioned_by = ARRAY [ 'year',	'month' ]",
        ', year(tbl.o_orderdate) as "year" , month(tbl.o_orderdate) as "month"',
    ),
    "lineitem": (
        ", partitioned_by = ARRAY [ 'ship_year',	'ship_month' ]",
        ', year(tbl.l_shipdate) as "ship_year" , month(tbl.l_shipdate) as "ship_month"',
    ),
}


@task.branch(task_id="should_delete_raw", task_display_name="Delete Raw Enabled?")
def should_delete_raw(**kwargs):

    return "yes_delete" if kwargs["params"]["drop_raw_when_done"] else None


with DAG(
    dag_id="create_larger_tpch_dataset",
    dag_display_name="Create a large TPC-H dataset",
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    params={
        "size": Param(
            default="100GB",
            enum=["100GB", "3TB", "30TB"],
            description="Size of the dataset to create, this is based on the unoptimized version of the data.",
            title="Dataset Size (unoptimized)",
        ),
        "s3_bucket": Param(
            default="athena-mb-test",
            description="Bucket to store the data in.",
            type="string",
            title="S3 Bucket",
        ),
        "s3_prefix": Param(
            default="tpch_100gb/",
            description="Prefix to store the data under. Must be either / (root of bucket) or a string ending in slash, e.g. some/prefix/",
            type="string",
            title="S3 Prefix",
            pattern=r"(^\/$|^[^\/].*\/$)",
        ),
        "drop_raw_when_done": Param(
            default=True,
            description="Drop the Raw tables once the data is stored in a more optimized format (parquet).",
            title="Drop Raw Data when processed",
            type="boolean",
        ),
        "database_name": Param(
            default="tpch100gb",
            description="Name of the Glue Database to store the tables in. Will be created if it doesn't exist.",
            type="string",
        ),
        "athena_workgroup": Param(
            default="primary",
            type="string",
            description="Name of the Athena Workgroup to use.",
        ),
        "athena_output_location_s3_uri": Param(
            default="s3://aws-athena-query-results-689680084035-eu-central-1/",
            type="string",
            pattern=r"^s3:\/\/[a-z0-9-_]*\/.*$",
            title="Athena Result location",
            description="S3 URI to store the Athena results under, e.g. s3://my-bucket/and_prefix/.",
        ),
    },
) as dag:

    create_db_if_not_exists = AthenaOperator(
        task_id="create_database_if_not_exists",
        task_display_name="Create the database if it doesn't exist.",
        query="create database if not exists {{params.database_name}}",
        database="{{params.database_name}}",
        workgroup="{{params.athena_workgroup}}",
        output_location="{{params.athena_output_location_s3_uri}}",
    )

    yes_delete_raw_table = EmptyOperator(
        task_id="yes_delete", task_display_name="Yes, enabled."
    )
    should_delete_raw() >> yes_delete_raw_table

    create_optimized_sql = textwrap.dedent(
        """
        create table if not exists {table_name} with (
            external_location = 's3://{bucket_name}/{prefix}/'
            , format = 'PARQUET'
            {with_additional}
        ) as
        select tbl.*
            {select_additional}
            
        from {table_name}_raw as tbl;
        """
    )
    drop_raw_table_sql = "drop table if exists {table_name}_raw"

    for table_name in TABLE_NAMES:

        with TaskGroup(
            group_id=f"process_{table_name}",
            tooltip=f"Create and optimize the {table_name} table.",
        ):

            query = TABLE_NAME_TO_SQL_TEMPLATE[table_name].format(
                table_name=f"{table_name}_raw",
                suffix=textwrap.dedent(
                    """
                    ROW FORMAT DELIMITED
                    FIELDS TERMINATED BY '|'
                    STORED AS TEXTFILE
                    LOCATION 's3://{bucket_name}/{prefix}';
                    """.format(
                        bucket_name=SOURCE_S3_BUCKET,
                        prefix=f"TPC-H/2.18/{{{{params.size}}}}/{table_name}/",
                    )
                ),
            )

            create_raw_table = AthenaOperator(
                task_id=f"create_{table_name}_raw_table",
                task_display_name=f"Create the {table_name}_raw table.",
                query=query,
                database="{{params.database_name}}",
                workgroup="{{params.athena_workgroup}}",
                output_location="{{params.athena_output_location_s3_uri}}",
            )

            create_db_if_not_exists >> create_raw_table

            with_additional, select_additional = TABLE_TO_OPT_WITH_AND_SELECT.get(
                table_name, ("", "")
            )

            create_optimized_table = AthenaOperator(
                task_id=f"create_{table_name}_optimized_table",
                task_display_name=f"Create the optimized {table_name} table.",
                query=create_optimized_sql.format(
                    table_name=table_name,
                    bucket_name="{{params.s3_bucket}}",
                    prefix=f"{{{{params.s3_prefix}}}}{table_name}",
                    with_additional=with_additional,
                    select_additional=select_additional,
                ),
                database="{{params.database_name}}",
                workgroup="{{params.athena_workgroup}}",
                output_location="{{params.athena_output_location_s3_uri}}",
            )
            create_raw_table >> create_optimized_table

            drop_raw_table = AthenaOperator(
                task_id=f"drop_{table_name}_raw_table",
                task_display_name=f"Drop the {table_name}_raw table.",
                query=drop_raw_table_sql.format(
                    table_name=table_name,
                ),
                database="{{params.database_name}}",
                workgroup="{{params.athena_workgroup}}",
                output_location="{{params.athena_output_location_s3_uri}}",
            )
            create_optimized_table >> drop_raw_table

            yes_delete_raw_table >> drop_raw_table
