
import os

import aws_cdk.aws_apigateway as apigateway
import aws_cdk.aws_codebuild as codebuild
import aws_cdk.aws_codecommit as codecommit
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda_python as _lambda
import aws_cdk.aws_lambda_event_sources as lambda_event_sources
import aws_cdk.aws_sns as sns
import aws_cdk.aws_ssm as ssm
import aws_cdk.aws_s3 as s3

from aws_cdk import core

MANUAL_APPROVAL_STAGE_NAME = "Approval"
MANUAL_APPROVAL_ACTION_NAME = "approve-before-publication"

class CdkPipelineSlackopsStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        repository = codecommit.Repository(
            self,
            "slackops-repository",
            repository_name="slackops-pipeline-repo",
            description="Repo for the SlackOps Pipeline Demo",
        )

        website_bucket = s3.Bucket(
            self,
            "website-bucket",
            removal_policy=core.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            public_read_access=True,
            website_index_document="index.html"
        )

        manual_approval_topic = sns.Topic(
            self,
            "manual-approval-notification",
        )

        artifact_bucket = s3.Bucket(
            self,
            "artifact-bucket",
            removal_policy=core.RemovalPolicy.DESTROY
        )

        source_artifact = codepipeline.Artifact(artifact_name="Source")
        deployment_artifact = codepipeline.Artifact(artifact_name="Deployment")

        pipeline = codepipeline.Pipeline(
            self,
            "slackops-pipeline",
            artifact_bucket=artifact_bucket,
            stages=[
                codepipeline.StageOptions(
                    stage_name="Source",
                    actions=[
                        codepipeline_actions.CodeCommitSourceAction(
                            repository=repository,
                            branch="master",
                            output=source_artifact,
                            action_name="Source"
                        )
                    ]
                ),
                codepipeline.StageOptions(
                    stage_name="Build",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            input=source_artifact,
                            action_name="Build",
                            project=codebuild.PipelineProject(
                                self,
                                "build-project",
                                build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml"),
                                environment=codebuild.BuildEnvironment(
                                    build_image=codebuild.LinuxBuildImage.STANDARD_5_0
                                ),
                            ),
                            outputs=[deployment_artifact]
                        )
                    ]
                ),
                codepipeline.StageOptions(
                    stage_name=MANUAL_APPROVAL_STAGE_NAME,
                    actions=[
                        codepipeline_actions.ManualApprovalAction(
                            action_name=MANUAL_APPROVAL_ACTION_NAME,
                            additional_information="Please Approve the Deployment",
                            notification_topic=manual_approval_topic,
                        )
                    ]
                ),
                codepipeline.StageOptions(
                    stage_name="Deploy",
                    actions=[
                        codepipeline_actions.S3DeployAction(
                            bucket=website_bucket,
                            input=deployment_artifact,
                            access_control=s3.BucketAccessControl.PUBLIC_READ,
                            action_name="deploy-to-s3"
                        )
                    ]
                )
            ]
        )

        # Build the API Gateway to record the approval or rejection

        rest_api = apigateway.RestApi(
            self,
            "slackops-apigw",
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
            )
        )

        root_resource = rest_api.root.add_resource("v1")

        approval_resource = root_resource.add_resource("approval")

        api_gateway_role = iam.Role(
            self,
            "slackops-apigw-role",
            assumed_by=iam.ServicePrincipal(
                service="apigateway.amazonaws.com",
            )
        )
        api_gateway_role.add_to_policy(
            iam.PolicyStatement(
                actions=["codepipeline:PutApprovalResult"],
                resources=[
                    pipeline.pipeline_arn + "/*"
                ]
            )
        )

        # Double curlies to make str.format work
        mapping_template = """
#set($token = $input.params("token"))
#set($response = $input.params("response"))
{{
   "actionName": "{action_name}",
   "pipelineName": "{pipeline_name}",
   "result": {{ 
      "status": "$response",
      "summary": ""
   }},
   "stageName": "{stage_name}",
   "token": "$token"
}}
        """.format(
            action_name="approve-before-publication",
            pipeline_name=pipeline.pipeline_name,
            stage_name="Approval",
        )

        approval_integration = apigateway.AwsIntegration(
            service="codepipeline",
            action="PutApprovalResult",
            integration_http_method="POST",
            options=apigateway.IntegrationOptions(
                credentials_role=api_gateway_role,
                request_parameters={
                    "integration.request.header.x-amz-target": "'CodePipeline_20150709.PutApprovalResult'",
                    "integration.request.header.content-type": "'application/x-amz-json-1.1'",
                },
                passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
                request_templates={
                    "application/json": mapping_template
                },
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code='400',
                        selection_pattern="4\d{2}",
                        response_parameters={
                            'method.response.header.error': 'integration.response.body'
                        }
                    ),
                    apigateway.IntegrationResponse(
                        status_code='500',
                        selection_pattern="5\d{2}",
                        response_parameters={
                            'method.response.header.error': 'integration.response.body'
                        }
                    )
                ]
            )
        )

        approval_method = approval_resource.add_method(
            http_method="GET",
            request_validator=apigateway.RequestValidator(
                self,
                "request-validator",
                rest_api=rest_api,
                request_validator_name="ParamValidator",
                validate_request_parameters=True
            ),
            request_parameters={
                "method.request.querystring.token": True,
                "method.request.querystring.response": True, # Approved / Rejected
            },
            method_responses=[
                apigateway.MethodResponse(
                    status_code='400',
                    response_parameters={
                        'method.response.header.error': True
                    }
                ),
                apigateway.MethodResponse(
                    status_code='500',
                    response_parameters={
                        'method.response.header.error': True
                    }
                )
            ],
            integration=approval_integration,
        )


        # Notification mechanism

        ssm_parameter_webhook = ssm.StringParameter(
            self,
            "slackops-webhook-parameter",
            string_value="<replace-me>",
            parameter_name="/slackops/webhook-url"
        )

        notification_lambda = _lambda.PythonFunction(
            self,
            "slackops-notification",
            entry=os.path.join(os.path.dirname(__file__), "..", "src"),
            index="index.py",
            handler="notification_handler",
            environment={
                "WEBHOOK_URL_PARAMETER": ssm_parameter_webhook.parameter_name,
                "API_ENDPOINT": rest_api.url_for_path("/v1/validations"),
            }
        )

        notification_lambda.add_event_source(
            lambda_event_sources.SnsEventSource(
                topic=manual_approval_topic
            )
        )

        ssm_parameter_webhook.grant_read(notification_lambda)

        # Outputs

        core.CfnOutput(
            self,
            "repositoryHttps",
            value=repository.repository_clone_url_http
        )

        core.CfnOutput(
            self,
            "repositorySSH",
            value=repository.repository_clone_url_ssh
        )

        core.CfnOutput(
            self,
            "websiteUrl",
            value=website_bucket.bucket_website_url
        )
