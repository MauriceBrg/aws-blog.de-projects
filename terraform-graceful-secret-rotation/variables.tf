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

