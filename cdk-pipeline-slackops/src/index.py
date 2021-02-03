import json
import os

import boto3
import requests

WEBHOOK_PARAMETER_NAME = os.environ.get("WEBHOOK_URL_PARAMETER", "/slackops/webhook-url")
API_ENDPOINT = os.environ.get("API_ENDPOINT", "https://e6f0vj492m.execute-api.eu-central-1.amazonaws.com/prod/v1/approval")

def build_slack_message(event: dict):
    custom_data = event["approval"]["customData"]
    expires = event["approval"]["expires"]
    token = event["approval"]["token"]
    approval_review_link = event["approval"]["approvalReviewLink"]
    pipeline_name = event["approval"]["pipelineName"]
    stage_name = event["approval"]["stageName"]
    return {
	"blocks": [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"The Pipeline *{pipeline_name}* is currently in stage *{stage_name}* and waiting for your feedback to continue."
			}
		},
		{
			"type": "actions",
			"elements": [
                {
                    "type": "button",
                    "url": approval_review_link,
                    "text": {
                        "type": "plain_text",
                        "text": "View Details",
                    }
                },
				{
					"type": "button",
                    "style": "primary",
                    "url": f"{API_ENDPOINT}?token={token}&response=Approved",
					"text": {
						"type": "plain_text",
						"text": "Approve",
						"emoji": True,
					}
				},
				{
					"type": "button",
                    "style": "danger",
                    "url": f"{API_ENDPOINT}?token={token}&response=Rejected",
					"text": {
						"type": "plain_text",
						"text": "Reject",
						"emoji": True,
					}
				}
			]
		}
	]
}

def handle_pipeline_event(event: dict):

    print(json.dumps(event))
    

    # Get the webhook URL
    ssm_client = boto3.client("ssm")
    webhook_url = ssm_client.get_parameter(
        Name=WEBHOOK_PARAMETER_NAME
    )["Parameter"]["Value"]

    # Build the slack message
    slack_message = build_slack_message(event)
    
    # Send the message
    response = requests.post(
        url=webhook_url,
        json=slack_message
    )

    print(response.text)

def notification_handler(event: dict, context):
    
    print(json.dumps(event))

    pipeline_event = json.loads(event["Records"][0]["Sns"]["Message"])

    handle_pipeline_event(pipeline_event)

if __name__ == "__main__":
    with open(os.path.join(os.path.dirname(__file__), "sample_event.json")) as file:
        sample_pipeline_event = json.load(file)

        handle_pipeline_event(sample_pipeline_event)