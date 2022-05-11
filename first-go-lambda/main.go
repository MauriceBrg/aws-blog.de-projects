package main

import (
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/rds"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
)

func getRDSClient() *rds.RDS {
	awsRegion := "eu-central-1"

	// Apparently we need to create a session first
	// Must makes things crash if something goes wrong
	session := session.Must(session.NewSession(&aws.Config{Region: &awsRegion}))

	// We then use this session to get an rds client
	return rds.New(session)
}

func listDBInstances() ([]*rds.DBInstance, error) {

	rdsClient := getRDSClient()

	response, err := rdsClient.DescribeDBInstances(&rds.DescribeDBInstancesInput{})

	return response.DBInstances, err
}

func stopDBInstance(dbInstanceIdentifier *string) error {

	rdsClient := getRDSClient()

	_, err := rdsClient.StopDBInstance(&rds.StopDBInstanceInput{
		DBInstanceIdentifier: dbInstanceIdentifier,
	})

	return err
}

func dbInstanceShouldBeStopped(dbInstance *rds.DBInstance) bool {

	hasTag := false

	for _, tag := range dbInstance.TagList {
		if *tag.Key == "PUT_ME_TO_SLEEP" && *tag.Value == "YES" {
			hasTag = true
			break
		}
	}

	isAvailable := *dbInstance.DBInstanceStatus == "available"

	return isAvailable && hasTag
}

func putDBInstancesToSleep() error {

	dbInstances, err := listDBInstances()
	if err != nil {
		return err
	}

	for _, dbInstance := range dbInstances {
		if dbInstanceShouldBeStopped(dbInstance) {
			err := stopDBInstance(dbInstance.DBInstanceIdentifier)
			if err != nil {
				return err
			}
		}
	}

	return nil

}

func HandleLambdaEvent(event events.CloudWatchEvent) error {
	return putDBInstancesToSleep()
}

func main() {

	lambda.Start(HandleLambdaEvent)

}
