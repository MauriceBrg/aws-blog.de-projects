import difflib
import logging
import sys

import requests

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler(sys.stdout))
LOGGER.setLevel(logging.DEBUG)


def fetch_cloudfront_pops() -> list[dict]:

    more_content = True
    page = 0

    all_items = []

    while more_content:
        more_content = False

        response = requests.get(
            "https://aws.amazon.com/api/dirs/items/search",
            params={
                "item.directoryId": "cf-map-pins",
                "sort_by": "item.additionalFields.y",
                "sort_order": "desc",
                "size": "500",
                "item.locale": "en_US",
                "page": page,
            },
            timeout=10,
        )

        for item_container in response.json()["items"]:
            more_content = True

            item = item_container["item"]
            item["tags"] = item_container["tags"]

            all_items.append(item)

        page += 1

    return all_items


def is_regional_edge_pop(item: dict) -> bool:

    for tag in item["tags"]:
        if tag["id"].endswith("#regional-edge-caches"):
            return True
    return False


def get_region_info() -> dict[str, dict]:
    global_infrastructure = requests.get(
        "https://b0.p.awsstatic.com/locations/1.0/aws/current/locations.json",
        timeout=10,
    ).json()

    return {
        key: value
        for key, value in global_infrastructure.items()
        if value["type"] == "AWS Region"
    }


if __name__ == "__main__":
    all_pops = fetch_cloudfront_pops()
    regional_pops = [pop for pop in all_pops if is_regional_edge_pop(pop)]

    regional_pop_names_and_descriptions = [
        (x["additionalFields"]["pinName"], x["additionalFields"]["pinDescription"])
        for x in regional_pops
    ]
    LOGGER.info("Regional Edge Caches: %s", regional_pop_names_and_descriptions)

    region_info = get_region_info()

    for regional_pop_name, description in regional_pop_names_and_descriptions:
        matches = difflib.get_close_matches(
            regional_pop_name, region_info.keys(), n=1, cutoff=0.4
        )

        if not matches:
            LOGGER.debug(
                "Failed to match %s by name, trying description (%s)",
                regional_pop_name,
                description,
            )
            matches = difflib.get_close_matches(
                description, region_info.keys(), n=1, cutoff=0.3
            )
            if not matches:
                raise RuntimeError(f"Unable to map {regional_pop_name}")

        region_name = matches[0]
        api_name = region_info[region_name]["code"]
        LOGGER.info(
            "The CF-Name %s most closely matches %s (%s)",
            regional_pop_name,
            region_name,
            api_name,
        )

