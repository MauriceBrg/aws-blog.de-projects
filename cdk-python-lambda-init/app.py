#!/usr/bin/env python3

from aws_cdk import core

from infrastructure.cdk_python_lambda_init_stack import CdkPythonLambdaInitStack


app = core.App()
CdkPythonLambdaInitStack(app, "cdk-python-lambda-init")

app.synth()
