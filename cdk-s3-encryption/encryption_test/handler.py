import os
import unittest

import boto3
from botocore.exceptions import ClientError

def print_debug_information_and_raise(client_error: ClientError):

    operation = client_error.operation_name
    code = client_error.response['Error']['Code']
    x_amz_request_id = client_error.response['ResponseMetadata']['HTTPHeaders']["x-amz-request-id"]
    x_amz_id_2 = client_error.response['ResponseMetadata']['HTTPHeaders']['x-amz-id-2']
    print(f"ClientError / Operation { operation } /  Code: { code } / x-amz-request-id: {x_amz_request_id} / x-amz-id-2: {x_amz_id_2}")

    raise client_error


class EncryptionTestCases(unittest.TestCase):

    def setUp(self):
        self.s3_resource = boto3.resource("s3")
        self.sse_s3_bucket = os.environ["SSE_S3_BUCKET"]
        self.sse_kms_bucket = os.environ["SSE_KMS_BUCKET"]
        self.sse_kms_key_id = os.environ["KMS_FOR_S3"]
        self.other_kms_id = os.environ["DIFFERENT_KMS"]

        self.s3_http_resource = boto3.resource("s3", use_ssl=False)
    
    def test_put_without_encryption_to_sse_s3_bucket_should_work(self):
        """Default encryption should take over when we specify nothing"""

        try:
            sse_s3_obj = self.s3_resource.Object(
                self.sse_s3_bucket,
                "test/test_put_without_encryption_to_sse_s3_bucket_should_work"
            )
            sse_s3_obj.put(
                Body="test_put_without_encryption_to_sse_s3_bucket_should_work"
            )

            # Clean up after us
            sse_s3_obj.delete()

        except ClientError as err:
            print_debug_information_and_raise(err)
    
    def test_put_without_encryption_to_sse_kms_bucket_should_work(self):
        """Default encryption should take over when we specify nothing"""

        try:
            sse_kms_obj = self.s3_resource.Object(
                self.sse_kms_bucket,
                "test/test_put_without_encryption_to_sse_kms_bucket_should_work"
            )
            sse_kms_obj.put(
                Body="test_put_without_encryption_to_sse_kms_bucket_should_work"
            )

            # Clean up after us
            sse_kms_obj.delete()

        except ClientError as err:
            print_debug_information_and_raise(err)

    def test_put_with_explicit_encryption_to_sse_s3_bucket_should_work(self):
        """Explicitly setting the correct encryption type should work"""

        sse_s3_obj = self.s3_resource.Object(
            self.sse_s3_bucket,
            "test/test_put_with_explicit_encryption_to_sse_s3_bucket_should_work"
        )
        sse_s3_obj.put(
            ServerSideEncryption="AES256",
            Body="test_put_with_explicit_encryption_to_sse_s3_bucket_should_work"
        )

        # Clean up after us
        sse_s3_obj.delete()

    def test_put_with_explicit_encryption_to_sse_kms_bucket_should_work(self):
        """Explicitly setting the correct encryption type should work"""

        sse_kms_obj = self.s3_resource.Object(
            self.sse_kms_bucket,
            "test/test_put_with_explicit_encryption_to_sse_kms_bucket_should_work"
        )
        sse_kms_obj.put(
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId=self.sse_kms_key_id,
            Body="test_put_with_explicit_encryption_to_sse_kms_bucket_should_work"
        )

        # Clean up after us
        sse_kms_obj.delete()

    def test_sse_kms_to_sse_s3_fails(self):
        """
        Assert that we get an error when we try to store SSE-KMS encrypted
        objects in the bucket that is SSE-S3 encrypted.
        """

        with self.assertRaises(ClientError):
            sse_s3_obj = self.s3_resource.Object(
                self.sse_s3_bucket,
                "test/test_sse_kms_to_sse_s3_fails"
            )
            sse_s3_obj.put(
                Body="test_sse_kms_to_sse_s3_fails",
                ServerSideEncryption="aws:kms",
                SSEKMSKeyId=self.sse_kms_key_id
            )
            sse_s3_obj.delete()
    
    def test_sse_s3_to_sse_kms_fails(self):
        """
        Assert that we get an error when we try to store SSE-S3 encrypted
        objects in the bucket that is SSE-KMS encrypted.
        """

        with self.assertRaises(ClientError):
            sse_kms_obj = self.s3_resource.Object(
                self.sse_kms_bucket,
                "test/test_sse_s3_to_sse_kms_fails"
            )
            sse_kms_obj.put(
                Body="test_sse_s3_to_sse_kms_fails",
                ServerSideEncryption="AES256",
            )
            sse_kms_obj.delete()
    
    def test_wrong_kms_key_fails(self):
        """
        Assert that a put request to the SSE-KMS encrypted bucket with a
        different KMS key fails.
        """
        with self.assertRaises(ClientError):
            sse_kms_obj = self.s3_resource.Object(
                self.sse_kms_bucket,
                "test/test_wrong_kms_key_fails"
            )
            sse_kms_obj.put(
                Body="test_wrong_kms_key_fails",
                ServerSideEncryption="aws:kms",
                SSEKMSKeyId=self.other_kms_id
            )
            sse_kms_obj.delete()

    def test_unencrypted_upload_fails_for_sse_kms_bucket(self):
        """
        Assert that we get an encryption if we try to upload via HTTP.
        """

        with self.assertRaises(ClientError):

            sse_kms_obj = self.s3_http_resource.Object(
                self.sse_kms_bucket,
                "test/test_http_upload_fails"
            )

            sse_kms_obj.put(
                Body="test_http_upload_fails"
            )
            sse_kms_obj.delete()


    def test_unencrypted_upload_fails_for_sse_s3_bucket(self):
        """
        Assert that we get an encryption if we try to upload via HTTP.
        """

        with self.assertRaises(ClientError):

            sse_s3_obj = self.s3_http_resource.Object(
                self.sse_s3_bucket,
                "test/test_http_upload_fails"
            )

            sse_s3_obj.put(
                Body="test_http_upload_fails"
            )
            sse_s3_obj.delete()


def lambda_handler(event, context):
    # Execute the test cases
    suite = unittest.TestLoader().loadTestsFromTestCase(EncryptionTestCases)
    runner = unittest.TextTestRunner()
    result = runner.run(suite)

    errors_and_failures = len(result.failures) + len(result.errors)

    assert errors_and_failures == 0, f"All tests should be green - {errors_and_failures} aren't."

if __name__ == "__main__":
    lambda_handler({},{})
