#!/usr/bin/env python3

import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3

from aws_cdk import core


class ExportingStack(core.Stack):

    exported_role_a: iam.Role
    exported_role_b: iam.Role

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.exported_role_a = iam.Role(
            self,
            "exporting-role-a",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        self.exported_role_b = iam.Role(
            self,
            "exporting-role-b",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        # compat_output = core.CfnOutput(
        #     self,
        #     id="will-be-overwritten",
        #     # TODO: Update the value according to your environment
        #     value=f"arn:aws:iam::{core.Aws.ACCOUNT_ID}:role/export-exportingroleb66286D65-CZGEAEVHHA32",
        #     export_name="export:ExportsOutputFnGetAttexportingroleb66286D65ArnE09A9A52"
        # )
        # compat_output.override_logical_id("ExportsOutputFnGetAttexportingroleb66286D65ArnE09A9A52")

class ImportingStack(core.Stack):

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        role_a: iam.Role,
        role_b: iam.Role,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        test_bucket = s3.Bucket(
            self,
            "some-bucket",
            removal_policy=core.RemovalPolicy.DESTROY
        )

        test_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                principals=[
                    role_a,
                    # role_b
                ],
                resources=[
                    test_bucket.arn_for_objects("*"),
                    test_bucket.bucket_arn
                ]
            )
        )



app = core.App()
export = ExportingStack(app, "export")

ImportingStack(
    app,
    "import",
    role_a=export.exported_role_a,
    role_b=export.exported_role_b
)

app.synth()
