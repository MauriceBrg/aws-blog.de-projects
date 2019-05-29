#!/usr/bin/env bash

# How to: . switch_environment.sh ENVIRONMENT_NAME

STAGE=$1

if [[ ! -d "environments/${STAGE}" ]]; then
    echo "The environment '${STAGE}' doesn't exist under environments/ - please check the spelling!"
    echo "These environments are available:"
    ls environments/
    return 1
fi

if [[ -f environments/${STAGE}/backend.config ]]; then
    # Configure the Backend
    echo "Running: terraform init -backend-config=environments/${STAGE}/backend.config ."
    terraform init -backend-config=environments/${STAGE}/backend.config .
else
    echo "The backend configuration is missing at environments/${STAGE}/backend.config!"
    return 2
fi

if [[ -f "environments/${STAGE}/variables.tfvars" ]]; then
    # Configure a function that runs terraform with the variables attached
    # --> "tf apply" will run "terraform apply -var-file=path/to/variables.tfvars"
    echo "The alias 'tf' runs terraform with the correct variable file when appropriate"
    tf () {

        # List of commands that can accept the -var-file argument
        sub_commands_with_vars=(apply destroy plan)

        # List of commands that accept the backend argument
        sub_commands_with_backend=(init)

        # ${@:2} means that we append all of the arguments after tf init

        if [[ " ${sub_commands_with_vars[@]} " =~ " $1 " ]]; then
            # Only some of the subcommands can work with the -var-file argument
            echo "Running: terraform $1 -var-file=environments/${STAGE}/variables.tfvars ${@:2}"
            terraform $1 -var-file=environments/${STAGE}/variables.tfvars ${@:2}
        elif [[ " ${sub_commands_with_backend[@]} " =~ " $1 " ]]; then
            # Only some sub commands require the backend configuration
            echo "Running: terraform init -backend-config=environments/${STAGE}/backend.config ${@:2}"
            terraform init -backend-config=environments/${STAGE}/backend.config ${@:2}
        else
            echo "Running: terraform $@"
            terraform $@
        fi

    }
else
    echo "Couldn't find the variables file here: environments/${STAGE}/variables.tfvars "
    echo "Won't set up the tf function!"
    return 3
fi

