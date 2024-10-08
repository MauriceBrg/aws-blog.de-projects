import argparse
import base64
import json
import logging
import pathlib
import sys

import boto3

from metadata import MetadataStorage, ImageLinkRecord


LOGGER = logging.getLogger(__name__)

CHARS_BEFORE_LINK = 1000
CHARS_BEHIND_LINK = 1000


def get_alt_text_for_image(
    article_content: str, image_link_record: ImageLinkRecord
) -> str:

    client = boto3.client("bedrock-runtime")

    beginning = article_content.find(image_link_record["original_link_md"])
    start_idx = max(0, beginning - CHARS_BEFORE_LINK)
    end_idx = min(
        len(article_content),
        beginning + len(image_link_record["original_link_md"]) + CHARS_BEHIND_LINK,
    )
    article_content_short = article_content[start_idx:end_idx]

    prompt = f"""
    Summarize the following image into a single sentence and keep your summary as brief as possible.

    You can use this text between <start> and <end> as context, the image is refered to as {image_link_record['original_link_md']}
    <start>
    {article_content_short}
    <end>
    Exclusively output the content for an HTML Image alt-attribute, one line only, no code, no introduction, only the text, focus on accessibility.
    """

    # Read the image file
    with open(image_link_record["abs_img_path"], "rb") as image_file:
        image_data = image_file.read()

    payload = {
        "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
        "input": {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64.b64encode(image_data).decode("utf-8"),
                            },
                        },
                    ],
                }
            ],
        },
    }

    response = client.invoke_model(
        modelId=payload["modelId"], body=json.dumps(payload["input"])
    )
    response_body = response["body"].read()

    result = json.loads(response_body.decode("utf-8"))
    alt_tag = result.get("content", [{}])[0].get("text")

    return alt_tag


def main():
    LOGGER.addHandler(logging.StreamHandler(sys.stdout))
    LOGGER.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Generate the text for the alt-tags for all image "
        "links that are in status INFERENCE_REQUIRED.",
    )
    parser.add_argument(
        "--metadata-file",
        type=pathlib.Path,
        help="Path to store the metadata at, default metadata.json in the "
        "current working directory.",
        default="metadata.json",
    )

    args = parser.parse_args()

    metadata_path = str(args.metadata_file)
    metadata = MetadataStorage(metadata_path)

    file_to_links = metadata.get_by_status("INFERENCE_REQUIRED")
    for file_path, links in file_to_links.items():

        article_content = pathlib.Path(file_path).read_text("utf-8")

        for link in links:

            alt_text = get_alt_text_for_image(
                article_content=article_content, image_link_record=link
            )
            new_link = f"![{alt_text}]({link['rel_img_path']})"

            link["new_alt_text"] = alt_text
            link["status"] = "READY_TO_UPDATE"
            link["new_link_md"] = new_link
            LOGGER.debug(
                "The alt-text for the image '%s' in %s will be \n\n%s\n",
                link["rel_img_path"],
                file_path,
                alt_text,
            )

            metadata.save(link)
            metadata.serialize()  # Kinda inefficient, but if something breaks it's consistent.


if __name__ == "__main__":
    main()
