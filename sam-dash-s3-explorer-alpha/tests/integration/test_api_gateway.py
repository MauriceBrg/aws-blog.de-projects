import boto3
import pytest
import requests


STACK_NAME = "sam-dash-s3-explorer-alpha"
APIGW_URL_OUTPUT_NAME = "ServerlessDashApi"


class TestApiGateway:

    @pytest.fixture()
    def api_gateway_url(self):
        """Get the API Gateway URL from Cloudformation Stack outputs"""

        client = boto3.client("cloudformation")

        try:
            response = client.describe_stacks(StackName=STACK_NAME)
        except Exception as e:
            raise RuntimeError(
                f"Cannot find stack {STACK_NAME} \n"
                f'Please make sure a stack with the name "{STACK_NAME}" exists'
            ) from e

        stacks = response["Stacks"]
        stack_outputs = stacks[0]["Outputs"]
        api_outputs = [
            output
            for output in stack_outputs
            if output["OutputKey"] == APIGW_URL_OUTPUT_NAME
        ]

        if not api_outputs:
            raise KeyError(f"{APIGW_URL_OUTPUT_NAME} not found in stack {STACK_NAME}")

        return api_outputs[0]["OutputValue"]  # Extract url from stack outputs

    def test_api_gateway(self, api_gateway_url):
        """Call the API Gateway endpoint and check the response"""
        response = requests.get(api_gateway_url, timeout=10)

        assert response.status_code == 401
        loading_text = "Unauthorized"
        assert loading_text in response.text
