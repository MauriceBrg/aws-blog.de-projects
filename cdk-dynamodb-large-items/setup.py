import setuptools

CDK_VERSION = "1.92.0"
with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="cdk_dynamodb_large_items",
    version="0.0.1",

    description="Demo App to test how long it takes to request different large dynamodb items from different lambdas.",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Maurice Borgmeier",

    package_dir={"": "infrastructure"},
    packages=setuptools.find_packages(where="infrastructure"),

    install_requires=[
        f"aws-cdk.aws-dynamodb=={CDK_VERSION}",
        f"aws-cdk.aws-lambda=={CDK_VERSION}",
        f"aws-cdk.aws-lambda-event-sources=={CDK_VERSION}",
        f"aws-cdk.aws-sns=={CDK_VERSION}",
        f"aws-cdk.aws-s3=={CDK_VERSION}",
        f"aws-cdk.core=={CDK_VERSION}",
    ],

    python_requires=">=3.7",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)