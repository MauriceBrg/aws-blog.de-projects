"""
Dash Page that acts like a file explorer for S3.
"""

import boto3
import dash
import dash_bootstrap_components as dbc
from dash import html, Input, Output, State, callback, MATCH


dash.register_page(__name__, path="/", name="S3 Explorer (alpha)")

INLINE_TEXT_RENDER_LIMIT_IN_MB = 2
INLINE_TEXT_RENDER_FILE_SUFFIXES = (
    ".json",
    ".yaml",
    ".yml",
    ".ini",
    ".config",
    ".py",
    ".js",
    ".sh",
    ".java",
    ".rb",
    ".txt",
)


def layout():
    """
    Called by Dash to render the base layout.
    """

    return dbc.Container(
        children=[
            dbc.Form(
                children=[
                    dbc.Label(
                        "Select a bucket to explore",
                        html_for="select-s3-bucket",
                        className="text-muted",
                    ),
                    dbc.Select(
                        id="select-s3-bucket", options=[], placeholder="Select a bucket"
                    ),
                ]
            ),
            html.H4("Bucket Content", className="mt-2"),
            html.Div(id="bucket-contents"),
        ],
    )


@callback(
    Output("select-s3-bucket", "options"),
    Input("select-s3-bucket", "id"),
)
def populate_s3_bucket_selector(_select_children):

    s3_client = boto3.client("s3")
    bucket_list = s3_client.list_buckets()["Buckets"]

    options = [{"label": item["Name"], "value": item["Name"]} for item in bucket_list]

    return options


def _s3_path_to_bucket_and_key(s3_path: str) -> tuple[str, str]:

    bucket_name = s3_path.removeprefix("s3://").split("/")[0]
    object_key = s3_path.removeprefix(f"s3://{bucket_name}/")

    return bucket_name, object_key


def render_download_link(s3_path):
    bucket_name, key = _s3_path_to_bucket_and_key(s3_path)
    filename = s3_path.split("/")[-1]

    s3_client = boto3.client("s3")

    download_url: str = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": bucket_name,
            "Key": key,
        },
        ExpiresIn=60 * 60,
    )

    return html.A(
        href=download_url,
        download=filename,
        children=["Download Object"],
        className="btn btn-link",
    )


def render_icon(s3_path: str) -> html.I:
    """
    Return an icon based on the probable type of the s3 path / object.
    """

    icon = "bi-file-earmark"

    if s3_path.endswith("/"):
        icon = "bi-folder-fill"

    elif s3_path.endswith((".json", ".py", ".yaml", ".yml")):
        icon = "bi-file-earmark-code"

    elif s3_path.endswith((".zip", ".gz", ".tar")):
        icon = "bi-file-earmark-zip"

    elif s3_path.endswith((".txt",)):
        icon = "bi-file-text"

    elif s3_path.endswith((".pdf",)):
        icon = "bi-file-pdf"

    elif s3_path.endswith((".csv", ".parquet", ".avro")):
        icon = "bi-file-spreadsheet"

    elif s3_path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")):
        icon = "bi-file-earmark-image"

    return html.I(className=f"bi {icon} me-2")


def render_directory_list_item(s3_path: str) -> dbc.ListGroupItem:
    """
    Renders an item in a directory listing.
    """

    _, object_key = _s3_path_to_bucket_and_key(s3_path)

    label = (
        object_key.removesuffix("/").split("/")[-1] + "/"
        if object_key.endswith("/")
        else object_key.split("/")[-1]
    )

    output = dbc.ListGroupItem(
        children=[
            html.Span(
                id={
                    "type": "s3-item",
                    "index": s3_path,
                },
                style={"cursor": "pointer", "width": "100%", "display": "block"},
                children=[render_icon(s3_path), label],
                n_clicks=0,
            ),
            html.Div(
                id={
                    "type": "s3-item-content",
                    "index": s3_path,
                },
            ),
        ],
    )

    return output


def render_inline_text(s3_path: str):
    """
    Display text-based objects in a textarea with the option to update or download it.
    """

    bucket_name, key = _s3_path_to_bucket_and_key(s3_path)

    content_as_str = (
        boto3.client("s3")
        .get_object(
            Bucket=bucket_name,
            Key=key,
        )["Body"]
        .read()
        .decode("utf-8")
    )

    inline_text_area = dbc.Textarea(
        id={"type": "inline-text", "index": s3_path},
        value=content_as_str,
        style={
            "font-family": "monospace",
            "width": "100%",
            "min-height": "400px",
        },
        className="mt-3 mb-2",
    )

    save_changes_button = dbc.Button(
        id={"type": "inline-text-save-button", "index": s3_path},
        title=f"Save Changes to {s3_path}",
        children=["Save Changes"],
        outline=True,
        color="primary",
    )

    return [
        inline_text_area,
        save_changes_button,
        html.Span(
            id={"type": "inline-text-save-message", "index": s3_path},
            className="ms-2 text-muted",
        ),
        render_download_link(s3_path),
    ]


@callback(
    Output({"type": "inline-text-save-message", "index": MATCH}, "children"),
    Input({"type": "inline-text-save-button", "index": MATCH}, "n_clicks"),
    State({"type": "inline-text", "index": MATCH}, "value"),
    State({"type": "inline-text", "index": MATCH}, "id"),
    prevent_initial_call=True,
)
def save_edited_text(_, new_text: str, text_area_id: dict):

    print(_, new_text, text_area_id)

    s3_path = text_area_id["index"]

    bucket_name, key = _s3_path_to_bucket_and_key(s3_path)
    boto3.client("s3").put_object(
        Bucket=bucket_name, Key=key, Body=new_text.encode("utf-8")
    )

    return "Changes saved."


def render_s3_object_details(s3_path: str):
    bucket_name, key = _s3_path_to_bucket_and_key(s3_path)

    s3_client = boto3.client("s3")
    metadata = s3_client.head_object(Bucket=bucket_name, Key=key)

    filename = s3_path.split("/")[-1]
    size_in_bytes = metadata["ContentLength"]
    content_type = metadata["ContentType"]

    size_in_mibibyte = size_in_bytes / 1024 / 1024

    if (
        filename.endswith(INLINE_TEXT_RENDER_FILE_SUFFIXES)
        and size_in_mibibyte < INLINE_TEXT_RENDER_LIMIT_IN_MB
    ):
        return render_inline_text(s3_path)

    return html.Div(
        children=[
            html.Ul(
                children=[
                    html.Li(f"Size (Bytes): {size_in_bytes}"),
                    html.Li(f"Content-Type: {content_type}"),
                ]
            ),
            render_download_link(s3_path),
        ]
    )


def render_directory_listing(s3_path: str):

    # Note: strictly speaking we'd have to check the content type, but this is good enough
    is_directory = s3_path.endswith("/")
    if not is_directory:
        return render_s3_object_details(s3_path)

    bucket_name, key_prefix = _s3_path_to_bucket_and_key(s3_path)

    s3_client = boto3.client("s3")
    list_response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Delimiter="/",
        Prefix=key_prefix,
    )

    common_prefixes = [obj["Prefix"] for obj in list_response.get("CommonPrefixes", [])]
    items = [obj["Key"] for obj in list_response.get("Contents", [])]

    all_items = common_prefixes + items

    list_items = [
        render_directory_list_item(f"s3://{bucket_name}/{item}") for item in all_items
    ]

    if not list_items:
        # Nothing to show
        return dbc.Alert("No objects found here...", color="light")

    return dbc.ListGroup(list_items, class_name="mt-1")


@callback(
    Output("bucket-contents", "children"),
    Input("select-s3-bucket", "value"),
)
def handle_bucket_selection(bucket_name):
    """
    Executed when a bucket is selected in the top-level dropdown.
    """

    if bucket_name is None:
        return [dbc.Alert("No bucket selected.", color="light")]

    s3_path = f"s3://{bucket_name}/"

    return render_directory_listing(s3_path)


@callback(
    Output({"type": "s3-item-content", "index": MATCH}, "children"),
    Input({"type": "s3-item", "index": MATCH}, "n_clicks"),
    State({"type": "s3-item", "index": MATCH}, "id"),
    prevent_initial_call=True,
)
def handle_click_on_directory_item(n_clicks, current_level):
    """
    Executed when someone clicks on a directory item - folder or object.
    """

    is_open = n_clicks % 2 == 1

    if not is_open:
        return []

    s3_path: str = current_level["index"]

    return render_directory_listing(s3_path)
