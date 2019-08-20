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


# @xray_recorder.capture('## lambda_handler')
def lambda_handler(event, context):
    try:
        logger.info('event: {}'.format(event))
        blue_asg_name = event.get('blue', {}).get('asg_name')

        asg_info = asg.describe_auto_scaling_groups(
            AutoScalingGroupNames=[blue_asg_name])
        # blue_lc_name = asg_info['AutoScalingGroups'][0]\
        #    ['LaunchConfigurationName']
        asg_param = asg_info.get('AutoScalingGroups')[0]
        blue_lc_name = asg_param.get('LaunchConfigurationName')

        asg_result = delete_asg(blue_asg_name)

        # TODO AMI,LCはしばらく残してロールバックできるようにする
        # lc_result = delete_lc(blue_lc_name)
        return dict(asg_delete_result=asg_result)

    except ClientError as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise e

    except Exception as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise e


def delete_asg(asg_name):
    response = asg.delete_auto_scaling_group(
        AutoScalingGroupName=asg_name
    )
    return response


def delete_lc(lc_name):
    response = asg.delete_launch_configuration(
        LaunchConfigurationName=lc_name
    )
    return response
