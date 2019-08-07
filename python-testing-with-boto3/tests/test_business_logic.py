import boto3
import unittest

from moto import mock_s3

import src.business_logic as bl

class TestBusinessLogic(unittest.TestCase):

    def setUp(self):

        self.s3_mock = mock_s3()
        self.s3_mock.start()
        
        res = boto3.resource('s3', region_name="eu-central-1")
        res.create_bucket(Bucket="bucket_name")

    def test_upload_report_to_s3(self):


        bl.upload_report_to_s3("tests/fixtures/demo_report.csv", "bucket_name", "object_key")

        s3_client = boto3.client('s3')
        # We'd get a Client Error 404 if this didn't work
        response = s3_client.head_object(Bucket="bucket_name", Key="object_key")
        self.assertIsNotNone(response)

    def tearDown(self):
        self.s3_mock.stop()

if __name__ == "__main__":
    unittest.main()
