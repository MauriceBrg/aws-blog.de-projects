# Provisioning TPC-H datasets in Athena

This directory contains two Airflow DAGs that are designed to provision the TPC-H dataset in Athena.
The only dependency that they require is the AWS provider (`pip install apache-airflow-providers-amazon`).

Drop them in your DAG directory (after inspecting the code to make sure I'm not destroying your system) and you'll see two new DAGs show up:

1. **Create a 10GB sized TPC-H dataset** which can only provision the 10GB (uncompressed) dataset. In Parquet form it's significantly less.
2. **Create a large TPC-H dataset** which allows you to pick between 100 GB, 3 TB or 30TB datasets.

For more details, check out the accompanying blog post: [Making the TPC-H dataset available in Athena using Airflow](https://www.tecracer.com/blog/2024/08/making-the-tpc-h-dataset-available-in-athena-using-airflow.html)