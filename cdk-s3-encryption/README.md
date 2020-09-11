# Demo on enforcing S3 encryption

This belongs to our article on [enforcing encryption standards on S3 objects](/2020/09/enforcing-encryption-standards-on-s3-objects.html).

## Deployment steps

1. Install the CDK (`npm install -g aws-cdk`)
2. Create a virtual environment in python `python3 -m venv .env` and activate it `source .env/bin/activate`
3. Install the dependencies via `pip install -r requirements.txt`
4. Deploy the infrastructure with `cdk deploy --require-approval never`
5. Run the lambda function that has been deployed and investigate the tests as well as the bucket policies
6. (Optional) Delete everything with `cdk destroy`