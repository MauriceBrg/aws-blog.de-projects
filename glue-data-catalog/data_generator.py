import csv
import os
import random

import boto3
import faker

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data", "products_partitioned")

COLUMNS = ["supplier_name", "product_name", "price", "quantity", "weight"]

RECORDS_PER_FILE = 1_000

FAKE = faker.Faker("en")

def generate_record(partition_name: str, price, with_weight: bool):
    
    record = {
        "supplier_name": partition_name,
        "product_name": FAKE.first_name(),
        "price": price,
        "quantity": random.randint(1, 10_000),
        "weight": random.randint(1, 50) if with_weight else None,
    }

    return record

def write_records_to_csv(records: list, file_name: str):

    os.makedirs(os.path.dirname(file_name), exist_ok=True)

    with open(file_name, "w") as output:

        writer = csv.DictWriter(
            f=output,
            fieldnames=COLUMNS,
            delimiter=";",
            quotechar="\"",
            quoting=csv.QUOTE_NONNUMERIC,
        )

        writer.writeheader()

        for record in records:
            writer.writerow(record)


def generate_int_partition(partition_name: str, with_weight: bool):

    print(f"Generating supplier={partition_name}/data.csv")

    records = [
        generate_record(
            partition_name,
            random.randint(1, 10_000), with_weight
        )
        for _ in range(RECORDS_PER_FILE)
    ]

    file_name = os.path.join(
        OUTPUT_DIR,
        f"supplier={partition_name}/data.csv"
    )

    write_records_to_csv(records, file_name)

def generate_double_partition(partition_name: str, with_weight: bool):

    print(f"Generating supplier={partition_name}/data.csv")

    records = [
        generate_record(
            partition_name,
            round(random.uniform(1, 10_000), 2),
            with_weight
        )
        for _ in range(RECORDS_PER_FILE)]

    file_name = os.path.join(
        OUTPUT_DIR,
        f"supplier={partition_name}/data.csv"
    )

    write_records_to_csv(records, file_name)

def main():

    generate_int_partition(
        partition_name="int_with_weight",
        with_weight=True,
    )

    generate_int_partition(
        partition_name="int_without_weight",
        with_weight=False,
    )

    generate_double_partition(
        partition_name="double_with_weight",
        with_weight=True,
    )

    generate_double_partition(
        partition_name="double_without_weight",
        with_weight=False,
    )


if __name__ == "__main__":
    main()