## Setup

1. Create a new virtual environment and activate it: `python3 -m venv .venv  && source .venv/bin/activate`
2. Install the dependencies: `pip install -r requirements.txt`
3. Generate Sample Data in the `data/` directory using `python data_generator.py`
    This will generate data for four partitions with different characteristics
4. Create an S3 Bucket, it's name will be `$BucketName`
5. Copy the data into the S3 Bucket using the AWS CLI: `aws s3 sync data/ s3://$BucketName/`

    It should look something like this:

    ```terminal
    $ aws s3 sync data/ s3://trc-maurice-data/
    upload: data/products_partitioned/supplier=int_without_weight/data.csv to s3://trc-maurice-data/products_partitioned/supplier=int_without_weight/data.csv
    upload: data/products_partitioned/supplier=double_without_weight/data.csv to s3://trc-maurice-data/products_partitioned/supplier=double_without_weight/data.csv
    upload: data/products_partitioned/supplier=double_with_weight/data.csv to s3://trc-maurice-data/products_partitioned/supplier=double_with_weight/data.csv
    upload: data/products_partitioned/supplier=int_with_weight/data.csv to s3://trc-maurice-data/products_partitioned/supplier=int_with_weight/data.csv
    ```

6. Now we can create a database in the Glue Data Catalog, we'll refer to it as `$DatabaseName`
7. Create a crawler that crawls the data in `$BucketName`and adds the tables in `$DatabaseName`
8. Start the Crawler, it will create the `products_partitioned`table in `$DatabaseName`.
9. Now you can follow along with the blog posts.