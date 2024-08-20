import argparse
import logging
import os
import pathlib
import re
import sys

from metadata import make_image_link_record, ImageLink, MetadataStorage


IMAGE_LINKS_PATTERN = re.compile(
    r"(?P<full_match>!\[(?P<alt_text>.*)\]\((?P<path>.*)\))"
)
LOGGER = logging.getLogger(__name__)


def extract_image_links_from_markdown_doc(
    doc: str,
) -> list[ImageLink]:
    """
    Returns a list of image links found in a markdown doc.

    Parameters
    ----------
    doc : str
        The content of the doc to parse.

    Returns
    -------
    list[tuple[str, str | None, str]]
        List of tuples, the tuple contains the following:
        - str: exact string match of the image link (for search and replace)
        - str/None: alt-text (if it exists) or None
        - the path to the image (may be relative)
    """

    links = []

    for match in IMAGE_LINKS_PATTERN.finditer(doc):

        captured_patterns = match.groupdict()
        full_match = captured_patterns["full_match"]
        alt_text = (
            captured_patterns["alt_text"]
            if captured_patterns["alt_text"] != ""
            else None
        )
        path = captured_patterns["path"]

        links.append(ImageLink(full_match, alt_text, path))

    return links


def get_image_path(
    asset_paths: list[str], article_path: pathlib.Path, image_link: ImageLink
) -> pathlib.Path | None:

    potential_paths: list[pathlib.Path] = []
    image_path = pathlib.Path(image_link.path)
    image_path_without_leading_slash = str(image_path).removeprefix("/")
    image_path_rel = pathlib.Path(image_path_without_leading_slash)

    # May be an absolute path
    potential_paths.append(image_path)
    potential_paths.append(image_path_rel)

    # Relative to article path
    potential_paths.append(article_path.parent / image_path)
    potential_paths.append(article_path.parent / image_path_rel)

    # Current workdir
    potential_paths.append(pathlib.Path(os.getcwd()) / image_path)
    potential_paths.append(pathlib.Path(os.getcwd()) / image_path_rel)

    # Relative to any of the asset paths
    for asset_path in asset_paths:
        potential_paths.append(pathlib.Path(asset_path) / image_path)
        potential_paths.append(pathlib.Path(asset_path) / image_path_rel)

    for path in potential_paths:
        if path.exists():
            return path.resolve()

    return None


def main():
    LOGGER.addHandler(logging.StreamHandler(sys.stdout))
    LOGGER.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Extract image links from Markdown documents, verify the image"
        " exists, and store them in metadata storage.",
    )
    parser.add_argument(
        "markdown_base_dir",
        type=pathlib.Path,
        help="Parent directory that contains markdown files (will be searched recursively)",
    )
    parser.add_argument(
        "--asset-base-dir",
        type=pathlib.Path,
        help="Additional directory to consider when searching for the referenced images "
        "(relative to image links). It already looks for the images relative to the "
        "markdown document as well as the current working directory. If the path is "
        "absolute, it will also be found.",
    )
    parser.add_argument(
        "--metadata-file",
        type=pathlib.Path,
        help="Path to store the metadata at, default metadata.json in the "
        "current working directory.",
        default="metadata.json",
    )
    parser.add_argument(
        "--update-existing-alt",
        "--ue",
        help="Update existing alt texts for newly discovered links, default: False",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()

    article_base_bath: pathlib.Path = args.markdown_base_dir
    asset_paths = [args.asset_base_dir] or []
    markdown_docs = article_base_bath.glob("**/*.md", case_sensitive=False)

    metadata_path = str(args.metadata_file)
    metadata = MetadataStorage(metadata_path)

    for path in markdown_docs:
        LOGGER.debug("Parsing Markdown doc at: %s", path)

        article_content = path.read_text("utf-8")
        image_links = extract_image_links_from_markdown_doc(article_content)
        LOGGER.debug("Found %s image links", len(image_links))

        image_links_without_alt = [lnk for lnk in image_links if lnk.alt_text is None]
        LOGGER.debug("%s of these are missing alt-texts", len(image_links_without_alt))

        image_links_to_process = image_links_without_alt

        if args.update_existing_alt:
            LOGGER.debug("Also considering image links with existing alt text.")
            image_links_to_process = image_links

        for image_link in image_links_to_process:

            path_to_image = get_image_path(
                asset_paths=asset_paths, article_path=path, image_link=image_link
            )

            if path_to_image is None:
                LOGGER.warning(
                    "Could not find the image in path '%s' for article '%s', skipping this one.",
                    image_link.path,
                    path.name,
                )
                continue

            LOGGER.debug("Full path for %s is %s", image_link.path, path_to_image)
            record = make_image_link_record(
                original_alt_text=image_link.alt_text,
                article_path=str(path),
                rel_img_path=image_link.path,
                original_link_md=image_link.full_match,
                abs_img_path=str(path_to_image),
                status="INFERENCE_REQUIRED",
            )
            if metadata.has(record):
                LOGGER.debug("Image Link is already processed, skipping it.")
            else:
                metadata.save(record)

    LOGGER.info("Saving metadata to %s", metadata_path)
    metadata.serialize()


if __name__ == "__main__":

    sys.argv.append("--asset-base-dir")
    sys.argv.append(
        "/Users/mauriceborgmeier/projects/prv/mauricebrg.com/website/static"
    )
    sys.argv.append(
        "/Users/mauriceborgmeier/projects/prv/mauricebrg.com/website/content"
    )
    # sys.argv.append("--help")
    main()
