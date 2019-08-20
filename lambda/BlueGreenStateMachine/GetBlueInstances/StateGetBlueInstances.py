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
        blue = event.get('blue', {})
        logger.info('blue: {}'.format(blue))
        blue_asg_name = blue.get('asg_name')

        blue_instances = get_blue_instances(blue_asg_name)

        continue_terminate_loop = True if blue_instances == 0 else False

        blue.update(dict(blue_instances=blue_instances,
                         continue_terminate_loop=continue_terminate_loop))
        logger.info('blue: {}'.format(blue))
        return blue
    except ClientError as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise e

    except Exception as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise e


def get_blue_instances(blue_asg_name):
    asg_info = asg.describe_auto_scaling_groups(
        AutoScalingGroupNames=[blue_asg_name])
    logger.info('asg_info: {}'.format(asg_info))
    blue_asg_instances = len(asg_info['AutoScalingGroups'][0]['Instances'])
    return blue_asg_instances
