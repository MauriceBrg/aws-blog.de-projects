#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infrastructure import SfnRetriesErrorHandlingStack


app = cdk.App()
SfnRetriesErrorHandlingStack(
    app,
    "SfnRetriesErrorHandlingStack",
)

app.synth()
