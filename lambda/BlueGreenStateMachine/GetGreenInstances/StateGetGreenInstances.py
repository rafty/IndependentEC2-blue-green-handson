# -*- coding: utf-8 -*-
import logging
import boto3
from botocore.exceptions import ClientError
# from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch_all()

asg = boto3.client('autoscaling', region_name='ap-northeast-1')
ec2 = boto3.client('ec2', region_name='ap-northeast-1')


# @xray_recorder.capture('## lambda_handler')
def lambda_handler(event, context):

    try:
        logger.info('event: {}'.format(event))
        green = event.get('green')
        green_asg_name = green.get('asg_name')
        green_status = get_green_running_instances(green_asg_name)

        desired = green_status.get('desired_capacity')
        green_instances = green_status.get('green_instances')

        continue_loop = True if green_instances >= desired else False

        green.update(dict(desired=desired,
                          instances=green_instances,
                          continue_loop=continue_loop))
        logger.info('green: {}'.format(green))
        return green

    except ClientError as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise e

    except Exception as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise e


def get_green_running_instances(green_asg_name):
    try:
        # ASG Parameters
        asg_info = asg.describe_auto_scaling_groups(
            AutoScalingGroupNames=[green_asg_name])
        green_instances = running_instances(asg_info)

        asg_params = asg_info['AutoScalingGroups'][0]
        desired_capacity = asg_params.get('DesiredCapacity')
        return dict(green_instances=green_instances,
                    desired_capacity=desired_capacity)

    except ClientError as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise

    except Exception as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise


def running_instances(asg_info):
    logger.info('asg_info: {}'.format(asg_info))

    _instances = asg_info['AutoScalingGroups'][0]['Instances']
    logger.info('_instances: {}'.format(_instances))

    if not len(_instances):
        return 0

    instance_statuses = ec2.describe_instance_status(
        Filters=[{'Name': 'instance-status.status', 'Values': ['ok']},
                 {'Name': 'system-status.status', 'Values': ['ok']}],
        InstanceIds=[instance['InstanceId'] for instance in _instances])
    logger.info('instance_statuses: {}'.format(instance_statuses))

    instances = list(filter(
        lambda e: e['InstanceId'] in [e['InstanceId'] for e in
                                      instance_statuses['InstanceStatuses']],
        _instances))

    logger.info('instances: {}'.format(len(instances)))
    return len(instances)
