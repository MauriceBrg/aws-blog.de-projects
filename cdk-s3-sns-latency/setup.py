import setuptools


with open("README.md") as fp:
    long_description = fp.read()

CDK_VERSION = "1.72.0"


setuptools.setup(
    name="cdk_s3_sns_latency",
    version="0.0.1",

    description="An empty CDK Python app",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "."},
    packages=setuptools.find_packages(where="."),

    install_requires=[
        f"boto3==1.16",
        f"boto3-stubs",
        "click==7.1",
        f"aws-cdk.core=={CDK_VERSION}",
        f"aws-cdk.aws-dynamodb=={CDK_VERSION}",
        f"aws-cdk.aws-kms=={CDK_VERSION}",
        f"aws-cdk.aws-lambda=={CDK_VERSION}",
        f"aws-cdk.aws-lambda-event-sources=={CDK_VERSION}",
        f"aws-cdk.aws-sns=={CDK_VERSION}",
        f"aws-cdk.aws-s3=={CDK_VERSION}",
        f"aws-cdk.aws-s3-notifications=={CDK_VERSION}",
    ],

    python_requires=">=3.6",

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

    entry_points="""
    [console_scripts]
    measure=cdk_s3_sns_latency.cli:cli
    """
)
