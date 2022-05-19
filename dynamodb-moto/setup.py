from setuptools import setup

setup(
    name='lambda-function',
    version='0.0.1',
    package_dir={
        "": "src"
    },
    install_requires=[
        'boto3',
    ],
)