import boto3

def upload_report_to_s3(path_to_report, bucket_name, object_name):
    
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket_name)

    bucket.upload_file(path_to_report, object_name)
