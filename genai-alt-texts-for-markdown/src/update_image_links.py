import argparse
import logging
import pathlib
import sys
import typing

from metadata import MetadataStorage


LOGGER = logging.getLogger(__name__)


def main():
    LOGGER.addHandler(logging.StreamHandler(sys.stdout))
    LOGGER.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Update the articles with new alt texts. By default, "
        "changes will be in-place. You're expected to use the "
        "--destination-dir option or have the files in git if you want to"
        " roll back to a previous version.",
    )
    parser.add_argument(
        "--metadata-file",
        type=pathlib.Path,
        help="Path to store the metadata at, default metadata.json in the "
        "current working directory.",
        default="metadata.json",
    )
    parser.add_argument(
        "--destination-dir",
        type=pathlib.Path,
        help="Instead of updating everything in-place, write the updated files"
        " (incl. directories) to this directory. You probably only want to do"
        "that if you're paranoid.",
        default=None,
    )

    args = parser.parse_args()
    print(args)

    metadata_path = str(args.metadata_file)
    metadata = MetadataStorage(metadata_path)

    file_to_links = metadata.get_by_status("READY_TO_UPDATE")
    for file_path, links in file_to_links.items():

        LOGGER.info("Updating %s", file_path)
        article_content = pathlib.Path(file_path).read_text("utf-8")

        for link in links:

            article_content = article_content.replace(
                link["original_link_md"], link["new_link_md"]
            )
            link["status"] = "UPDATED"

            metadata.save(link)

        if args.destination_dir is not None:
            file_path = typing.cast(pathlib.Path, args.destination_dir / file_path)
            LOGGER.debug("Writing changes to %s", file_path)
            file_path.parent.mkdir(exist_ok=True, parents=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(article_content)
        # metadata.serialize()  # Kinda inefficient, but if something breaks it's consistent.


if __name__ == "__main__":
    # sys.argv.append("--destination-dir")
    # sys.argv.append("local")
    main()
