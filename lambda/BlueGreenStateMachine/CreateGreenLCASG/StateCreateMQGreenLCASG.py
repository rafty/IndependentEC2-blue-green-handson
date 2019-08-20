# -*- coding: utf-8 -*-
import re
import time
import datetime
import logging
import boto3
from botocore.exceptions import ClientError
# from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

logger = logging.getLogger()
logger.setLevel(logging.INFO)
patch_all()
asg = boto3.client('autoscaling', region_name='ap-northeast-1')
ssm = boto3.client('ssm', region_name='ap-northeast-1')


# event ->
# {
#     "project": "ec",
#     "blue": {
#       "asg_name": "ec-mqagt-dev-asg-2019-08-14-07-54-45"
#     },
#     "Wait": 30
# }
def extract_parameters_state_machine(event):
    try:
        blue_asg_name = event.get('blue').get('asg_name')
        project_name = event.get('project')
        return dict(blue_asg_name=blue_asg_name,
                    project_name=project_name)
    except Exception as e:
        logger.error('Error: {}'.format(str(e)))
        raise


# @xray_recorder.capture('## lambda_handler')
def lambda_handler(event, context):

    logger.info('event: {}'.format(event))
    # blue_asg_name = event.get('blue', {}).get('asg_name')
    # project_name = event.get('project')
    params = extract_parameters_state_machine(event)

    green_golden_ami_id = get_golden_ami_id(
        params.get('project_name'))

    green_asg_name = create_green_asg(
        params.get('blue_asg_name'),
        green_golden_ami_id)

    logger.info('green asg name: {}'.format(green_asg_name))
    return dict(asg_name=green_asg_name)


def get_golden_ami_id(project_name):
    try:
        green_golden_ami_id_param = '-'.join(
            [project_name, 'GreenGoldenAMIID'])
        response = ssm.get_parameter(Name=green_golden_ami_id_param)

        green_golden_ami_id = response.get('Parameter').get('Value')
        logger.info('GreenGoldenAMIID: {}'.format(green_golden_ami_id))
        return green_golden_ami_id
    except ssm.exceptions.ParameterNotFound as e:
        logger.exception(
            'SSM Parameter GreenGoldenAMIID Not found: {}'.format(e))
        raise e
    except Exception as e:
        logger.exception(
            'SSM Parameter Exception: {}'.format(e))
        raise e


def extract_auto_scaling_group(asg_info):
    try:
        asg = asg_info.get('AutoScalingGroups')[0]
        lc_name = asg.get('LaunchConfigurationName')
        vpczone_identifier = asg.get('VPCZoneIdentifier')
        min_size = asg.get('MinSize')
        max_size = asg.get('MaxSize')
        desired_capacity = asg.get('DesiredCapacity')
        tags = asg.get('Tags')
        return dict(
            lc_name=lc_name,
            vpczone_identifier=vpczone_identifier,
            min_size=min_size,
            max_size=max_size,
            desired_capacity=desired_capacity,
            tags=tags)
    except Exception as e:
        logger.error('Error: {}'.format(str(e)))
        raise


def extract_lifecycle_hooks(hooks):
    try:
        lifecycle_hook = hooks.get('LifecycleHooks')[0]

        lifecycle_hook_name = lifecycle_hook.get('LifecycleHookName')
        lifecycle_transition = lifecycle_hook.get('LifecycleTransition')

        return dict(
            lifecycle_hook_name=lifecycle_hook_name,
            lifecycle_transition=lifecycle_transition)
    except Exception as e:
        logger.error('Error: {}'.format(str(e)))
        raise


def extract_launch_configurations(lc_info):
    try:
        lc = lc_info.get('LaunchConfigurations')[0]
        instance_profile_name = lc.get('IamInstanceProfile')
        instance_type = lc.get('InstanceType')
        sg_string = ",".join(lc.get('SecurityGroups'))

        return dict(
            instance_profile_name=instance_profile_name,
            instance_type=instance_type,
            sg_string=sg_string)
    except Exception as e:
        logger.error('Error: {}'.format(str(e)))
        raise


def get_blue_parameters(blue_asg_name):

    try:
        # ASG Parameters
        asg_info = asg.describe_auto_scaling_groups(
            AutoScalingGroupNames=[blue_asg_name])
        asg_params = extract_auto_scaling_group(asg_info)

        # LC Parameters
        lc_info = asg.describe_launch_configurations(
            LaunchConfigurationNames=[asg_params.get('lc_name')])
        lc_params = extract_launch_configurations(lc_info)

        # Lifecycle Hook
        hooks = asg.describe_lifecycle_hooks(
            AutoScalingGroupName=blue_asg_name)
        hook_params = extract_lifecycle_hooks(hooks)

        parameters = dict(
            vpczone_identifier=asg_params.get('vpczone_identifier'),
            min_size=asg_params.get('min_size'),
            max_size=asg_params.get('max_size'),
            desired_capacity=asg_params.get('desired_capacity'),
            tags=asg_params.get('tags'),
            instance_profile_name=lc_params.get('instance_profile_name'),
            sg_string=lc_params.get('sg_string'),
            instance_type=lc_params.get('instance_type'),
            lifecycle_hook_name=hook_params.get('lifecycle_hook_name'),
            lifecycle_transition=hook_params.get('lifecycle_transition'))
        logger.info('blue_parameters: {}'.format(parameters))
        return parameters
    except Exception as e:
        logger.error('Error: {}'.format(str(e)))
        raise


def trim_name(blue_asg_name):
    trimmed_name = re.sub(r"-[0-9]+-[0-9]+-[0-9]+-[0-9]+-[0-9]+-[0-9]+$", "",
                          blue_asg_name)
    return trimmed_name


def create_green_asg_lc_name(blue_asg_name):
    trimmed_bule_asg_name = trim_name(blue_asg_name)
    time_stamp = time.time()
    time_stamp_string = datetime.datetime. \
        fromtimestamp(time_stamp). \
        strftime('%Y-%m-%d-%H-%M-%S')
    green_lc_name = 'LC ' + \
                    trimmed_bule_asg_name + \
                    '-' + \
                    time_stamp_string
    green_asg_name = \
        trimmed_bule_asg_name + '-' + time_stamp_string
    logger.info('Green LC Name: {}'.format(green_lc_name))
    logger.info('Green ASG Name: {}'.format(green_asg_name))
    return green_asg_name, green_lc_name


def create_green_asg(blue_asg_name, green_golden_ami_id):
    logger.info('blue_asg_name: {}, green_golden_ami_id: {}'.format(
        blue_asg_name, green_golden_ami_id))
    blue_params = get_blue_parameters(blue_asg_name)
    green_asg_name, green_lc_name = create_green_asg_lc_name(blue_asg_name)

    try:
        # create LC using instance from ASG,
        # only diff is the name of the new LC and new AMI
        response = asg.create_launch_configuration(
            SecurityGroups=[blue_params.get('sg_string')],
            LaunchConfigurationName=green_lc_name,
            ImageId=green_golden_ami_id,
            InstanceType=blue_params.get('instance_type'),
            IamInstanceProfile=blue_params.get('instance_profile_name'))
        logger.info('created new launch configuration '
                    'with new AMI ID: {}'.format(response))

        lifecycle_hook_specification_list = \
            [{
                'LifecycleHookName': blue_params.get('lifecycle_hook_name'),
                'LifecycleTransition': blue_params.get('lifecycle_transition')
            }]
        tags = create_tags(blue_params.get('tags'))

        logger.info('Create green ASG {} '
                    'with green launch configuration {} '
                    'which includes AMI {}.'.format(green_asg_name,
                                                    green_lc_name,
                                                    green_golden_ami_id))
        response = asg.create_auto_scaling_group(
            AutoScalingGroupName=green_asg_name,
            LaunchConfigurationName=green_lc_name,
            MinSize=blue_params.get('min_size'),
            MaxSize=blue_params.get('max_size'),
            DesiredCapacity=blue_params.get('desired_capacity'),
            VPCZoneIdentifier=blue_params.get('vpczone_identifier'),
            LifecycleHookSpecificationList=lifecycle_hook_specification_list,
            Tags=tags)
        logger.info('created new asg response: {}'.format(response))
        return green_asg_name

    except ClientError as e:
        logger.exception('ASG LC Creation Exception: {}'.format(e))
        raise e

    except Exception as e:
        logger.exception('ASG Exception: {}'.format(e))
        raise e


def create_tags(source_tags):
    logger.info('source_tags: {}'.format(source_tags))
    tags = list()
    for tag in source_tags:
        if not tag['Key'].startswith('aws:'):
            tags.append(dict(Key=tag['Key'],
                             Value=tag['Value'],
                             PropagateAtLaunch=tag['PropagateAtLaunch']))
    logger.info('tags: {}'.format(tags))
    return tags
