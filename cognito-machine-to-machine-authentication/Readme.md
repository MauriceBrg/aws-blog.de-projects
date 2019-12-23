# What this is

A demo that shows how you can do machine to machine communication with the API-Gateway.

## How to

1. Run `npm install`
2. Run `pip install -r requirements.txt`
3. Create a new CloudFormation stack with the `user-pool-stack.yml` and take not of the outputs (User Pool Id and ARN)
4. Update the `custom` section of the `serverless.yml` with references to the User Pool Id + Arn
5. Run `serverless deploy`
6. Log in to AWS, navigate to the User Pool, then to App Clients on the left and fetch the Client ID and Client Secret
7. Update the `auth_demo.py` with the values for the API-Gateway, Cognito-Domain and stuff like that - everything the `TODO`s mention
8. Run `python auth_demo.py` and you should see Hello World coming up in the console.

## Resources

- [Understanding Amazon Cognito user pool OAuth 2.0 grants](https://aws.amazon.com/blogs/mobile/understanding-amazon-cognito-user-pool-oauth-2-0-grants/) by Kevin Yarosh on the AWS Blog
- [Cognito Token Endpoint](https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html) - AWS Developer Guide