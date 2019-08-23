# Serverless-Framework Example of Automatic Certificate Creation

This is a project, which demonstrates how to create a Certificate from the AWS Certificate Manager using a CloudFormation custom resource.

> This is or will be accompanied by a blog post on [aws-blog.de](aws-blog.de) describing some of the details. If I remember I'll update this with a link to the post - if not, feel free to raise an Issue.

## Prerequisites

- NodeJS and npm
- Docker if you're not running linux
- Your own Hosted Zone in AWS

## Installation

Run `npm install` in this directory to install the Serverless Framework and the necessary plugins.

## How to

1. Edit the `serverless.yml`
2. Edit these keys to fit your use case:
   - `custom.Domain` - replace the `<update-me>` with the Domain Name you want your Wildcard Certificate for, this needs to be part of the Hosted Zone.
   - `custom.HostedZoneId` - the Id of the Hosted Zone that belongs to the Domain.
3. Run `serverless deploy` and after a few minutes you should see the Certificate being created in AWS

## Credits

I didn't write the custom resource myself - I used the custom resource by [Mark van Holsteijn](https://github.com/mvanholsteijn) of Binx.io which they described in a [blog post](https://binx.io/blog/2018/10/05/automated-provisioning-of-acm-certificates-using-route53-in-cloudformation/) worth reading. Their code is avaiblable under the Apache 2.0 license [here on Github](https://github.com/binxio/cfn-certificate-provider).
