# -*- coding: utf-8 -*-
import logging
import boto3
from botocore.exceptions import ClientError
# import layer
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch_all()

asg = boto3.client('autoscaling', region_name='ap-northeast-1')


# @xray_recorder.capture('## lambda_handler')
def lambda_handler(event, context):
    try:
        logger.info('event: {}'.format(event))
        blue = event.get('blue', {})
        blue_asg_name = blue.get('asg_name')

        result = stop_blue_asg(blue_asg_name)

        blue.update(dict(status='stopping'))
        logger.info('blue: {}'.format(blue))
        return blue

    except ClientError as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise e

    except Exception as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise e


def stop_blue_asg(blue_asg_name):
    try:
        asg_config = dict(AutoScalingGroupName=blue_asg_name,
                          MinSize=0,
                          MaxSize=0,
                          DesiredCapacity=0,
                          DefaultCooldown=0)
        response = asg.update_auto_scaling_group(**asg_config)
        logger.info(response)
        return response

    except ClientError as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise e

    except Exception as e:
        raise e
