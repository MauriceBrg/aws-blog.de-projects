# Maintaining multiple environments in Terraform

## Introduction

I recently started learning Terraform for some projects I'm working on. When I began doing that I was struggling with the staging-concept of Terraform. I did my research and came upon numerous [^numerous] articles and blogs that described ways to manage (multiple) environments or stages in Terraform. By the way - I'm going to use environment and stage interchangeably.

Since there didn't seem to be a canonical way to handle multiple environments, I decided to try and figure out my own solution.

[^numerous]: Just a small sample:
    - [Deploying Multiple Environments with Terraform](https://medium.com/capital-one-tech/deploying-multiple-environments-with-terraform-kubernetes-7b7f389e622)  - Capital One on Medium
    -  [Maintaining Multiple Environments with Terraform](https://learn.hashicorp.com/terraform/operations/maintaining-multiple-environments#overview) - Tutorial on the Hashicorp site
    -  [Question about this on stackoverflow.com](https://stackoverflow.com/questions/37005303/different-environments-for-terraform-hashicorp)


## Some Background

**What is an environment or stage?**

In this context I'm refering to an instance of an application and/or a group of infrastructure components.

**Why do I need multiple environments or stages?**

When Deploying Applications and/or Infrastructure you typically have multiple instances of that Application and/or Infrastructure.

There are multiple reasons why you might want to do this, some include:

- Separate instances for production, qa, testing and development
- Separate instances for each customer

**What are the specific challenges in Terraform?**

Terraform maintains it's perception or representation of an environment's state in a [.tfstate-File](https://www.terraform.io/docs/state/) - by default that's called `terraform.tfstate`. This file is very important, because without it, Terraform has no idea, which resources it has deployed and how they look like[^this_is_bad].

Because the good folks at Hashicorp know this, they invented a way to deal with this problem: [Remote Backends](https://www.terraform.io/docs/backends/types/index.html) for [Remote State](https://www.terraform.io/docs/state/remote.html). I won't go into much detail about this, but in essence this keeps a copy of your `terraform.tfstate` in a remote location and may enable collaboration. As AWS afficionados we obviously prefer the [S3-Backend](https://www.terraform.io/docs/backends/types/s3.html) :).

Different environments might use different kinds of backends to store there state, so **we need to have a way to separate backends for separate environments**.

However, that's only half of the story:

Your environments probably use different configurations. This can include separate Webservice-Endpoints for productive and non-productive stages, different server-sizing and much more. Terraform has - as many other tools do as well - the concept of [Variables](https://www.terraform.io/docs/configuration/variables.html) and [Variable-Files](https://www.terraform.io/docs/configuration/variables.html#variable-definitions-tfvars-files) (`.tfvars`) to deal with this. The latter can be passed as input to some Terraform commands, e.g.:

```shell
terraform apply -var-file=test.tfvars
```

This is the second challenge we need to deal with: **handle environment-specific variables**.

For my solution this boils down to the design goals discussed in the next section.

[^this_is_bad]: If you lose that file, your application will continue to work, but you could end up with a bunch of expensive resources distributed across the world
 and no idea how they fit together.

## Design Goals

The solution should be:

- easy to set up
- easy to use
- able to support environment-specific backends
- able to support environment-spcific variable files
- usable on Linux (if it works on Mac, that would be a nice benefit as well)

## Solution

My solution makes a few assumptions about its environment:

- it runs on Linux
- the user is lazy (you shouldn't extrapolate from yourself to others, but I can't help myself...)
- the project is structured like this:

```text
├── environments
│   ├── production
│   │   ├── backend.config
│   │   └── variables.tfvars
│   ├── qa
│   │   ├── backend.config
│   │   └── variables.tfvars
│   └── test
│       ├── backend.config
│       └── variables.tfvars
├── main.tf
└── switch_environment.sh
```

You might already be able to spot the pattern here - every directory under the `environments` directory is an environment or stage we can deploy into. Each of them has their own set of variables (`variables.tfvars`) and backend configuration (`backend.config`). You can use those files to configure your environment-specific values.

## How to

### Switching to an existing environment

Run the following command substituting `myenvironment` with the name of the environment you'd like to switch to:

```shell
. switch_environment.sh myenvironment
```

### Running Terraform commands

A feature of the environment switching script is, that it provides the `tf` shortcut for running `terraform` commands. This is not just an alias - it automatically adds the environments variable files to the commands that support them - here's an example:

```shell
tf apply
```

is the short form for

```shell
terraform apply -var-file=environments/currentstage/variables.tfvars
```

This should work for pretty much any terraform command - it even appends the backend configuration when you run:

```shell
tf init .
```

### Setting up a new environment

1. Create a new directory with the name of your environment under `environments/`
2. Add a `backend.config` under `environments/new_environment/` with your configuration for the Terraform backend
3. Add a `variables.tfvars` under `environments/new_environment/` with your configuration for the environments' variables
4. Switch to the new environment using:

    ```bash
    . switch_environment.sh new_environment
    ```

5. Read the next paragraph for a caveat about empty backends

### Switching to an environment with an **empty** backend storage

If you just set up your shiny new configuration for an even shinier new backend and you run the switch command `. switch_environment shiny_new_one` for the first time, Terraform may prompt you something like this:

```text
Backend configuration changed!

Terraform has detected that the configuration specified for the backend
has changed. Terraform will now check for existing state in the backends.


Do you want to copy existing state to the new backend?
  Pre-existing state was found while migrating the previous "s3" backend to the
  newly configured "s3" backend. No existing state was found in the newly
  configured "s3" backend. Do you want to copy this state to the new "s3"
  backend? Enter "yes" to copy and "no" to start with an empty state.

  Enter a value: no

```

This basically means: *"Hey, we noticed you changed to an empty environment, would you like us to copy the current state to that?"* - usually the answer should be no, since we created a new backend precisely to start with an empty slate.

## Wrapping up

Today I shared with you a script that might be useful if you work with multiple environments within your Terraform stack. The script is most likely not perfect - but it was good enough for my purpose. If you have ideas on how to improve it or some other kind of feedback - I'd love to hear from you. Just message me on twitter: [@Maurice_Brg](https://twitter.com/Maurice_Brg) or write me an email.