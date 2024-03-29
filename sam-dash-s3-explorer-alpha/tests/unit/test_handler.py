"""
Unit tests for the lambda handler
"""

import os
import json

import pytest

from frontend import app


def _load_json_event(name: str) -> dict:
    events_dir = os.path.join(os.path.dirname(__file__), "..", "..", "events")

    with open(os.path.join(events_dir, name), encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize(
    "event_file_name",
    ("root_request_from_apigw_domain.json", "root_request_from_custom_domain.json"),
)
def test_lambda_handler_loads_for_api_gw_and_custom_domain(event_file_name: str):
    """
    Test that we can handle events from the API Gateway and a custom domain.
    """

    # Arrange
    event = _load_json_event(event_file_name)

    # Act
    ret = app.lambda_handler(event, "")

    # Assert
    assert ret["statusCode"] == 200
    assert "Loading..." in ret["body"]
