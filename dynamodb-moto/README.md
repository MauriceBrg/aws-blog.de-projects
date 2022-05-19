# Getting started with testing access DynamoDB using moto

## Setup

1. Install the package:

    ```shell
    pip install -r requirements.txt
    ```

1. Install the dependencies for testing

    ```shell
    pip install -r dev-requirements.txt
    ```

## Run the tests

1. Run pytest:

    ```shell
    pytest
    ```
1. You should see an output like this:

```terminal
$ pytest --cov lambda_handler 
================================= test session starts ==================================
platform darwin -- Python 3.9.12, pytest-7.1.2, pluggy-1.0.0
rootdir: /wild-path/aws-blog-projects/dynamodb-moto
plugins: cov-3.0.0
collected 2 items                                                                      

tests/test_lambda_handler.py ..                                                  [100%]

---------- coverage: platform darwin, python 3.9.12-final-0 ----------
Name                    Stmts   Miss  Cover
-------------------------------------------
src/lambda_handler.py      24      0   100%
-------------------------------------------
TOTAL                      24      0   100%


================================== 2 passed in 0.66s ===================================
```