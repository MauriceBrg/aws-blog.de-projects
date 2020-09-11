#!/usr/bin/env python3

from aws_cdk import core

from infrastructure.cdk_s3_encryption_stack import CdkS3EncryptionStack

def main():

    app = core.App()
    CdkS3EncryptionStack(app, "cdk-s3-encryption")

    app.synth()

if __name__ == "__main__":
    main()