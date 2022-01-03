#!/usr/bin/env python3

from aws_cdk import core

from infrastructure.cdk_aurora_migration_demo_stack import SourceDatabaseStack


app = core.App()
SourceDatabaseStack(app, "cdk-aurora-migration-demo-source")

app.synth()
