import boto3
import os


def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name=os.environ['REGION'])
    instance_id = os.environ['INSTANCE_ID']

    response = ec2.stop_instances(InstanceIds=[instance_id])
    print(f"Stopped instance: {instance_id}")
    return {
        'statusCode': 200,
        'body': f'Stopped instance: {instance_id}'
    }
