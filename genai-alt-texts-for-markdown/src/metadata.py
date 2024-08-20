import collections
import json
import pathlib
import typing

Status = typing.Literal["INFERENCE_REQUIRED", "READY_TO_UPDATE", "UPDATED"]

ImageLink = collections.namedtuple("ImageLink", ["full_match", "alt_text", "path"])


class ImageLinkRecord(typing.TypedDict):
    original_alt_text: str | None
    new_alt_text: str | None
    article_path: str
    rel_img_path: str
    abs_img_path: str
    original_link_md: str
    new_link_md: str | None
    status: Status


def make_image_link_record(
    original_alt_text: str,
    article_path: str,
    rel_img_path: str,
    original_link_md: str,
    new_alt_text: str | None = None,
    abs_img_path: str | None = None,
    new_link_md: str | None = None,
    status: Status | None = None,
) -> ImageLinkRecord:

    return {
        "original_alt_text": original_alt_text,
        "article_path": article_path,
        "rel_img_path": rel_img_path,
        "original_link_md": original_link_md,
        "new_alt_text": new_alt_text,
        "abs_img_path": abs_img_path,
        "new_link_md": new_link_md,
        "status": status,
    }


class MetadataStorage:

    # Notes: rel_img_path should rarely change as opposed to the alt tag etc.

    _data: dict[str, dict[str, ImageLinkRecord]]
    _path: pathlib.Path

    def __init__(self, path: str | None = None) -> None:

        if path is None or not pathlib.Path(path).exists():
            self._data = {}
        else:
            self._data = json.loads(pathlib.Path(path).read_text("utf-8"))

        path: pathlib.Path = pathlib.Path(path)
        self._path = path

    def save(self, record: ImageLinkRecord) -> None:

        if record["article_path"] not in self._data:
            self._data[record["article_path"]] = {}

        self._data[record["article_path"]][record["rel_img_path"]] = record

    def has(self, record: ImageLinkRecord) -> bool:

        return (
            self._data.get(record["article_path"], {}).get(record["rel_img_path"])
            is not None
        )

    def get_by_status(self, status: Status) -> dict[str, list[ImageLinkRecord]]:

        results = {}

        for file_path, links in self._data.items():
            links_in_status = [
                link for link in links.values() if link["status"] == status
            ]

            if len(links_in_status) > 0:
                results[file_path] = links_in_status

        return results

    def serialize(self) -> None:

        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, sort_keys=True, indent=2)
