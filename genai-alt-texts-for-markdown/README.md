# Create alt-texts for images in Markdown files using GenAI

For context, I suggest you check out one of these blog posts, that explains the idea and background:

- [tecRacer Blog](https://www.tecracer.com/blog/2024/08/improving-accessibility-by-generating-image-alt-texts-using-genai.html)
- [dev.to](https://dev.to/aws-builders/improving-accessibility-by-generating-image-alt-texts-using-genai-22a4)
- [mauricebrg.com](https://mauricebrg.com/2024/08/improving-accessibility-by-generating-img-alt-texts-using-genai.html)

(Same content, [POSSE](https://indieweb.org/POSSE))

In a nutshell, the idea is to improve accessibility by generating `alt` texts in Markdown image links that help screen readers understand what the images in your content are about. It's primarily aimed at static websites built from Markdown documents but can also be used for regular README files etc. - more details in the aforementioned blog.

## Installation

**Prerequisites**

Your AWS SDK is set up and points to a region where Bedrock and the Anthropic Claude 3 Haiku LLMs are available.
If these are not in your default region or using the default credentials, use the environment variables `AWS_PROFILE` and `AWS_DEFAULT_REGION` to set this up appropriately.

1. Clone this repository
2. Create a new virtual environment (optional, `python3 -m venv .venv`)
3. Install the package using `pip install .`


## Usage

> I highly recommend you run this process only on files that are part of a git repository or otherwise version controlled, as it will make changes in-place.

This is a three step process. Once the tools are installed, you begin by helping it discover image links.
Use `discover-image-links` to do that. You want to point it at the directory where your Markdown documents are stored. It will search recursively from there to identify any Markdown documents. Check out the `--asset-base-dir` option outlined [below](#discover-image-links), which may come in useful if the script can't find the images. The script creates a `metadata.json` file, which is used by subsequent steps.

Next, we generate the alt texts based on the discovered links. Use `generate-alt-texts` to make the calls to Bedrock based on the discovered image links. This steps uses the aforementioned metadata to only generate texts that it doesn't have yet. Feel free to edit these in the `metadata.json` if you're unhappy with the results.

Last, we write the changes back to the files using the `update-image-links` utility, which will edit the Markdown files in-place. Now you should be done.

## CLI tools

### discover-image-links

```terminal
$ discover-image-links -h
usage: discover-image-links [-h] [--asset-base-dir ASSET_BASE_DIR] [--metadata-file METADATA_FILE]
                            [--update-existing-alt]
                            markdown_base_dir

Extract image links from Markdown documents, verify the image exists, and store them in metadata storage.

positional arguments:
  markdown_base_dir     Parent directory that contains markdown files (will be searched recursively)

options:
  -h, --help            show this help message and exit
  --asset-base-dir ASSET_BASE_DIR
                        Additional directory to consider when searching for the referenced images (relative
                        to image links). It already looks for the images relative to the markdown document as
                        well as the current working directory. If the path is absolute, it will also be
                        found.
  --metadata-file METADATA_FILE
                        Path to store the metadata at, default metadata.json in the current working
                        directory.
  --update-existing-alt, --ue
                        Update existing alt texts for newly discovered links, default: False
```

### generate-alt-texts

```terminal
$ generate-alt-texts -h
usage: generate-alt-texts [-h] [--metadata-file METADATA_FILE]

Generate the text for the alt-tags for all image links that are in status INFERENCE_REQUIRED.

options:
  -h, --help            show this help message and exit
  --metadata-file METADATA_FILE
                        Path to store the metadata at, default metadata.json in the current working
                        directory.
```

### update-image-links

```terminal
$ update-image-links -h
usage: update-image-links [-h] [--metadata-file METADATA_FILE] [--destination-dir DESTINATION_DIR]

Update the articles with new alt texts. By default, changes will be in-place. You're expected to use the
--destination-dir option or have the files in git if you want to roll back to a previous version.

options:
  -h, --help            show this help message and exit
  --metadata-file METADATA_FILE
                        Path to store the metadata at, default metadata.json in the current working
                        directory.
  --destination-dir DESTINATION_DIR
                        Instead of updating everything in-place, write the updated files (incl. directories)
                        to this directory. You probably only want to dothat if you're paranoid.
```

## Development

Install the package in editable mode `pip install -e .` and start hacking away :-)
