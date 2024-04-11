import json

from functools import lru_cache

from apig_wsgi import make_lambda_handler

from dash_app import build_app


@lru_cache(maxsize=5)
def build_handler(url_prefix: str) -> "Dash":

    # If there's not prefix, it's a custom domain
    if url_prefix is None or url_prefix == "":
        return make_lambda_handler(wsgi_app=build_app().server, binary_support=True)

    # If there's a prefix we're dealing with an API gateway stage
    # and need to return the appropriate urls.
    return make_lambda_handler(
        wsgi_app=build_app({"url_base_pathname": url_prefix}).server,
        binary_support=True,
    )


def get_raw_path(apigw_event: dict) -> str:
    """
    The "raw" path that was requested (i.e. including the stage prefix) is hidden
    under the requestContext object.
    """

    return apigw_event.get("requestContext", {}).get("path", apigw_event["path"])


def get_url_prefix(apigw_event: dict) -> str:
    """
    Returns the stage url prefix if the request arrives from the API Gateway and
    an empty string if it arrives via a custom domain.
    """

    apigw_stage_name = apigw_event["requestContext"]["stage"]
    prefix = f"/{apigw_stage_name}/"
    raw_path = get_raw_path(apigw_event)

    if raw_path.startswith(prefix):
        return prefix

    return ""


def lambda_handler(
    event: dict[str, "Any"], context: dict[str, "Any"]
) -> dict[str, "Any"]:

    # We need the path with the stage prefix, which the API gateway hides a bit.
    event["path"] = get_raw_path(event)
    handle_event = build_handler(get_url_prefix(event))

    response = handle_event(event, context)

    return response
