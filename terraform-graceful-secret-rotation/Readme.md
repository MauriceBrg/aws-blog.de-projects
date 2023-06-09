# Graceful Credential Rotation for IAM users

This is a demo accompanied by a blog post:

https://www.tecracer.com/blog/2023/06/advanced-credential-rotation-for-iam-users-with-a-grace-period.html

## Preparation

The main things to configure are stored in the `variables.tf`:

```lang-hcl
variable "iam-user-name" {
  type    = string
  default = "technical-user"
}

variable "rotate-credentials-every-n-days" {
  type        = number
  default     = 10
  description = "Rotate the credentials of the technical user every n days. Needs to be greater than credential-grace-period-in-minutes."
}

variable "credential-grace-period-in-minutes" {
  type        = number
  default     = 10
  description = "Allow for both the old and new credentials to be valid for n minutes before the old are deleted."
}
```

## Deployment

1. Run `terraform init`
1. Run `terraform plan` - you should see around 12 resources that it wants to create
1. Run `terraform apply` and confirm with yes
1. Log in to the AWS console, navigate to the newly created secret and trigger a secret rotation.
