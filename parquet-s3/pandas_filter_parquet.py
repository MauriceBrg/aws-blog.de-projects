"""
Demo of filtering a parquet file while reading it into a dataframe.
"""

import logging
import random
import sys
import typing
import uuid

from decimal import Decimal
from contextlib import contextmanager

import pandas as pd
import pandas.testing
import psutil
import pyarrow.dataset as ds
import pyarrow.parquet as pq

LOGGER = logging.getLogger(__name__)

# Update this with a bucket that you have access to.
BUCKET_NAME = "mbexchange"


def make_big_dataframe(n_rows: int, sort_frame: bool) -> pd.DataFrame:
    """Returns a dataframe with n_rows rows."""

    LOGGER.info("Generating a dataframe with %s rows", n_rows)
    sample_rows = [
        {
            "category": "blue",
            "number": Decimal("3.33"),
            "timestamp": pd.to_datetime("2022-10-01T05:00:00+01:00"),
        },
        {
            "category": "blue",
            "number": Decimal("7"),
            "timestamp": pd.to_datetime("2022-10-02T05:00:00+01:00"),
        },
        {
            "category": "gray",
            "number": Decimal("8.25"),
            "timestamp": pd.to_datetime("2022-10-03T05:00:00+01:00"),
        },
        {
            "category": "gray",
            "number": Decimal("7.3"),
            "timestamp": pd.to_datetime("2022-10-04T05:00:00+01:00"),
        },
        {
            "category": "red",
            "number": Decimal("20000.65"),
            "timestamp": pd.to_datetime("2022-10-05T05:00:00+01:00"),
        },
        {
            "category": "blue",
            "number": Decimal("3000000"),
            "timestamp": pd.to_datetime("2022-10-06T05:00:00+01:00"),
        },
    ]

    rows = map(lambda _: random.choice(sample_rows), range(n_rows))

    dataframe = pd.DataFrame(rows)
    dataframe["uuid"] = [uuid.uuid4().hex for _ in range(n_rows)]

    if sort_frame:
        dataframe.sort_values(by=["category", "timestamp", "number"], inplace=True)

    return dataframe


def create_test_file(file_name: str, n_rows: int, sort_frame=True) -> None:
    """Create a test parquet with the given name and number of rows."""
    frame = make_big_dataframe(n_rows, sort_frame)
    LOGGER.info("Got the dataframe")

    LOGGER.info(frame.dtypes)
    frame.to_parquet(file_name, index=False, row_group_size=200_000)


def get_memory_usage_in_mb(frame: pd.DataFrame) -> float:
    """Return the size of the dataframe including the index in MiB."""

    return frame.memory_usage(index=True, deep=True).sum() / 1024 / 1024


@contextmanager
def log_network_stats():
    """
    Logs bytes sent and received in KiB.
    """

    net_io_counters_start = psutil.net_io_counters()

    yield

    net_io_counters_end = psutil.net_io_counters()

    bytes_sent = net_io_counters_end.bytes_sent - net_io_counters_start.bytes_sent
    bytes_recv = net_io_counters_end.bytes_recv - net_io_counters_start.bytes_recv

    LOGGER.info(
        "Sent: %.2f KiB - Bytes received: %.2f KiB",
        bytes_sent / 1024,
        bytes_recv / 1024,
    )


RELEVANT_COLUMNS = ["category", "number", "timestamp"]

FILTER_TO_IMPLEMENTATION: typing.Dict[
    str, typing.Dict[str, typing.Callable[[str], pd.DataFrame]]
] = {
    "full frame / no filter": {
        "pandas-s3fs": lambda file_name: pd.read_parquet(
            file_name, columns=RELEVANT_COLUMNS
        ),
        "pyarrow": lambda file_name: ds.dataset(file_name, format="parquet")
        .to_table(columns=RELEVANT_COLUMNS)
        .to_pandas(),
    },
    "category == 'blue'": {
        "pandas-s3fs": lambda file_name: pd.read_parquet(
            file_name, columns=RELEVANT_COLUMNS, filters=ds.field("category") == "blue"
        ),
        "pyarrow": lambda file_name: ds.dataset(file_name, format="parquet")
        .to_table(columns=RELEVANT_COLUMNS, filter=ds.field("category") == "blue")
        .to_pandas(),
    },
    "category in ('red', 'gray')": {
        "pandas-s3fs": lambda file_name: pd.read_parquet(
            file_name,
            columns=RELEVANT_COLUMNS,
            filters=ds.field("category").isin(["red", "gray"]),
        ),
        "pyarrow": lambda file_name: ds.dataset(file_name, format="parquet")
        .to_table(
            columns=RELEVANT_COLUMNS, filter=ds.field("category").isin(["red", "gray"])
        )
        .to_pandas(),
    },
    "number <= 8.24": {
        "pandas-s3fs": lambda file_name: pd.read_parquet(
            file_name,
            columns=RELEVANT_COLUMNS,
            filters=ds.field("number") <= Decimal("8.24"),
        ),
        "pyarrow": lambda file_name: ds.dataset(file_name, format="parquet")
        .to_table(
            columns=RELEVANT_COLUMNS, filter=ds.field("number") <= Decimal("8.24")
        )
        .to_pandas(),
    },
    "timestamp <= '2022-10-03T17:00:00+12:00'": {
        "pandas-s3fs": lambda file_name: pd.read_parquet(
            file_name,
            columns=RELEVANT_COLUMNS,
            filters=ds.field("timestamp")
            <= pd.to_datetime("2022-10-03T17:00:00+12:00"),
        ),
        "pyarrow": lambda file_name: ds.dataset(file_name, format="parquet")
        .to_table(
            columns=RELEVANT_COLUMNS,
            filter=ds.field("timestamp") <= pd.to_datetime("2022-10-03T17:00:00+12:00"),
        )
        .to_pandas(),
    },
    "timestamp <= '2022-10-03T17:00:00+12:00' & category == 'blue'": {
        "pandas-s3fs": lambda file_name: pd.read_parquet(
            file_name,
            columns=RELEVANT_COLUMNS,
            filters=(
                ds.field("timestamp") <= pd.to_datetime("2022-10-03T17:00:00+12:00")
            )
            & (ds.field("category") == "blue"),
        ),
        "pyarrow": lambda file_name: ds.dataset(file_name, format="parquet")
        .to_table(
            columns=RELEVANT_COLUMNS,
            filter=(
                ds.field("timestamp") <= pd.to_datetime("2022-10-03T17:00:00+12:00")
            )
            & (ds.field("category") == "blue"),
        )
        .to_pandas(),
    },
}


def log_parquet_meta_info(file_name: str):
    """
    Logs some information about the row groups and statistics.
    """

    file = pq.ParquetFile(file_name)

    schema = file.metadata.schema

    LOGGER.info("Stats for %s", file_name)

    for i in range(len(schema)):
        LOGGER.info(
            "Column: %s - Physical Type: %s - Logical Type %s",
            schema.column(i).name,
            schema.column(i).physical_type,
            schema.column(i).logical_type,
        )

    for row_group in range(file.metadata.num_row_groups):
        rg_meta = file.metadata.row_group(row_group)
        LOGGER.info("%s Row Group %s %s", "=" * 10, row_group, "=" * 10)
        LOGGER.info(
            "Num Rows: %s, Total size: %.2f MiB",
            rg_meta.num_rows,
            rg_meta.total_byte_size / 1024 / 1024,
        )
        for col_num in range(len(schema)):

            col_meta = rg_meta.column(col_num)

            LOGGER.info(
                "Col: %s, Min: %s, Max: %s",
                schema.column(col_num).name,
                col_meta.statistics.min,
                col_meta.statistics.max,
            )


def main() -> None:
    """
    Runs the test, this is where you'd change if the frame should be sorted or not.
    """

    LOGGER.addHandler(logging.StreamHandler(sys.stdout))
    LOGGER.setLevel(logging.INFO)

    file_name = f"s3://{BUCKET_NAME}/sorted_test.parquet"

    create_test_file(file_name, 2_000_000, sort_frame=True)

    log_parquet_meta_info(file_name)

    for filter_scenario, implementations in FILTER_TO_IMPLEMENTATION.items():

        LOGGER.info("=" * 50)
        LOGGER.info("Filter Scenario: %s", filter_scenario)
        LOGGER.info("Requested columns: %s", ", ".join(RELEVANT_COLUMNS))

        frames: typing.List[pd.DataFrame] = []

        for name, implementation in implementations.items():

            LOGGER.info("-" * 30)
            LOGGER.info("Running %s implementation", name)
            with log_network_stats():

                frame = implementation(file_name)
                LOGGER.info("Memory usage: %.02f MiB", get_memory_usage_in_mb(frame))
                frames.append(frame)

        # Test that the two implementations yield the same result
        frame_1, frame_2, *_ = frames
        pandas.testing.assert_frame_equal(frame_1, frame_2)


if __name__ == "__main__":
    main()
