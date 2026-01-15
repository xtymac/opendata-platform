import boto3
import os


def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name=os.environ['REGION'])
    instance_id = os.environ['INSTANCE_ID']

    response = ec2.start_instances(InstanceIds=[instance_id])
    print(f"Started instance: {instance_id}")
    return {
        'statusCode': 200,
        'body': f'Started instance: {instance_id}'
    }
