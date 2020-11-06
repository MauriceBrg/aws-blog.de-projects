#!/usr/bin/env python3

from aws_cdk import core

from cdk_s3_sns_latency.cdk_s3_sns_latency_stack import CdkS3SnsLatencyStack


app = core.App()
CdkS3SnsLatencyStack(app, "cdk-s3-sns-latency")

app.synth()
