#!/usr/bin/env python3

from aws_cdk import core

from infrastructure.cdk_dynamodb_large_items_stack import CdkDynamoDBLargeItemsStack


app = core.App()
CdkDynamoDBLargeItemsStack(app, "cdk-dynamodb-large-items")

app.synth()
