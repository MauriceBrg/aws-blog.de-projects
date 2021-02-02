#!/usr/bin/env python3

from aws_cdk import core

from infrastructure.cdk_pipeline_slackops_stack import CdkPipelineSlackopsStack


app = core.App()
CdkPipelineSlackopsStack(app, "cdk-pipeline-slackops")

app.synth()
