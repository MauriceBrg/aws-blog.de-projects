import os

import aws_cdk.aws_iam as iam
import aws_cdk.aws_kms as kms
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_s3 as s3

from aws_cdk import core


class CdkS3EncryptionStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        kms_for_s3 = kms.Key(
            self,
            "kms-for-s3",
            description="Encryption key for the KMS encrypted S3 bucket",
            removal_policy=core.RemovalPolicy.DESTROY  # We don't want this to stick around after the demo
        )

        different_kms_key = kms.Key(
            self,
            "different-kms-key",
            description="Another KMS Key",
            removal_policy=core.RemovalPolicy.DESTROY  # We don't want this to stick around after the demo
        )

        bucket_with_sse_s3 = s3.Bucket(
            self,
            "bucket-with-sse-s3",
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        bucket_with_sse_s3.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=["s3:PutObject"],
                conditions={
                    "Null": {
                        "s3:x-amz-server-side-encryption": "false"
                    },
                    "StringNotEqualsIfExists": {
                        "s3:x-amz-server-side-encryption": "AES256"
                    }
                },
                principals=[iam.AnyPrincipal()],
                resources=[
                    bucket_with_sse_s3.arn_for_objects("*")
                ]
            )
        )

        bucket_with_sse_s3.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowSSLRequestsOnly",
                effect=iam.Effect.DENY,
                actions=["s3:*"],
                conditions={
                    "Bool": {
                        "aws:SecureTransport": "false"
                    }
                },
                principals=[iam.AnyPrincipal()],
                resources=[
                    bucket_with_sse_s3.arn_for_objects("*"),
                    bucket_with_sse_s3.bucket_arn
                ]
            )
        )


        bucket_with_sse_kms = s3.Bucket(
            self,
            "bucket-with-sse-kms",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=kms_for_s3
        )

        bucket_with_sse_kms.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=["s3:PutObject"],
                conditions={
                    "Null": {
                        "s3:x-amz-server-side-encryption": "false"
                    },
                    "StringNotEqualsIfExists": {
                        "s3:x-amz-server-side-encryption": "aws:kms"
                    }
                },
                principals=[iam.AnyPrincipal()],
                resources=[
                    bucket_with_sse_kms.arn_for_objects("*")
                ]
            )
        )

        bucket_with_sse_kms.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=["s3:PutObject"],
                conditions={
                    "StringNotEqualsIfExists": {
                        "s3:x-amz-server-side-encryption-aws-kms-key-id": kms_for_s3.key_arn
                    }
                },
                principals=[iam.AnyPrincipal()],
                resources=[
                    bucket_with_sse_kms.arn_for_objects("*")
                ]
            )
        )

        bucket_with_sse_kms.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowSSLRequestsOnly",
                effect=iam.Effect.DENY,
                actions=["s3:*"],
                conditions={
                    "Bool": {
                        "aws:SecureTransport": "false"
                    }
                },
                principals=[iam.AnyPrincipal()],
                resources=[
                    bucket_with_sse_kms.arn_for_objects("*"),
                    bucket_with_sse_kms.bucket_arn
                ]
            )
        )

        encryption_test_function = _lambda.Function(
            self,
            "encryption-test-function",
            code=_lambda.Code.from_asset(
                path=os.path.join(os.path.dirname(__file__), "..", "encryption_test")
            ),
            handler="handler.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_8,
            environment={
                "SSE_S3_BUCKET": bucket_with_sse_s3.bucket_name,
                "SSE_KMS_BUCKET": bucket_with_sse_kms.bucket_name,
                "KMS_FOR_S3": kms_for_s3.key_id,
                "DIFFERENT_KMS": different_kms_key.key_id,
            },
            timeout=core.Duration.seconds(15)
        )
        kms_for_s3.grant_encrypt_decrypt(encryption_test_function)
        different_kms_key.grant_encrypt_decrypt(encryption_test_function)
        bucket_with_sse_kms.grant_read_write(encryption_test_function)
        bucket_with_sse_s3.grant_read_write(encryption_test_function)
