# -*- coding: utf-8 -*-
import os
import time
import logging
import boto3
from botocore.exceptions import ClientError
# from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
patch_all()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

DOCUMENT_NAME = os.environ['DOCUMENT_NAME']
ssm = boto3.client("ssm")
asg = boto3.client('autoscaling')


def check_response(response):
    logger.info('check_response: {}'.format(response))
    try:
        if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
            return True
        else:
            return False

    except Exception as e:
        logger.error('Error: {}'.format(str(e)))
        return False


def list_document():
    try:
        document_filter_parameters = {'key': 'Name', 'value': DOCUMENT_NAME}
        response = ssm.list_documents(
            DocumentFilterList=[document_filter_parameters])
        logger.info('ssm.list_documents: {}'.format(response))
        return response
    except ClientError as e:
        logger.exception('SSM Exception: {}'.format(e))
        raise
    except Exception as e:
        logger.exception('SSM Exception: {}'.format(e))
        raise


def check_document():
    try:
        response = list_document()
        if check_response(response):
            logger.info('Documents list: {}'.format(response))
            if response['DocumentIdentifiers']:
                logger.info('Documents exists: {}'.format(response))
                return True
            else:
                return False
        else:
            logger.error('Documents list error: {}'.format(response))
            return False
    except KeyError as e:
        logger.exception('Document error: {}'.format(str(e)))
        return False
    except Exception as e:
        logger.exception('Document error: {}'.format(str(e)))
        return False


def send_command(instance_id, auto_scaling_group):
    # waits in accordance to a backoff mechanism.
    while True:
        time_wait = 1
        response = list_document()
        if any(response['DocumentIdentifiers']):
            break
        time.sleep(time_wait)
        time_wait += time_wait

    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName=DOCUMENT_NAME,
            Parameters={"AutoscalingGroupName": [auto_scaling_group]},
            TimeoutSeconds=1200)
        if check_response(response):
            logger.info('Command sent: {}'.format(response))
            return response['Command']['CommandId']
        else:
            logger.error('Command could not be sent: {}'.format(response))
            return None
    except Exception as e:
        logger.error('Command could not be sent: {}'.format(str(e)))
        return None


def check_command(command_id, instance_id):
    try:
        time_wait = 1
        while True:
            logger.info('ssm.list_command_invocations')
            response = ssm.list_command_invocations(
                CommandId=command_id,
                InstanceId=instance_id,
                Details=False)
            if check_response(response):
                if response.get('CommandInvocations'):
                    response_status = \
                        response['CommandInvocations'][0]['Status']
                else:
                    response_status = None

                if response_status is not None:
                    if response_status != 'Pending':
                        if response_status == 'InProgress' or \
                                response_status == 'Success':
                            logging.info(
                                'Status: {}'.format(response_status))
                            return True
                        else:
                            logging.error(
                                'ERROR '
                                'response_status: {}'.format(response_status))
                            return False
            time.sleep(time_wait)
            time_wait += time_wait
    except KeyError as e:
        logger.exception('KeyError error: {}'.format(str(e)))
        raise
    except ClientError as e:
        logger.exception('SSM Exception: {}'.format(e))
        raise
    except Exception as e:
        logger.error('check_command: {}'.format(str(e)))
        raise


def abandon_lifecycle(life_cycle_hook, auto_scaling_group, instance_id):
    try:
        response = asg.complete_lifecycle_action(
            LifecycleHookName=life_cycle_hook,
            AutoScalingGroupName=auto_scaling_group,
            LifecycleActionResult='ABANDON',
            InstanceId=instance_id
            )
        if check_response(response):
            logger.info('Lifecycle hook abandoned correctly: '
                        '{}'.format(response))
        else:
            logger.error('Lifecycle hook could not be abandoned: '
                         '{}'.format(response))
    except Exception as e:
        logger.error('Lifecycle hook abandon could not be executed: '
                     '{}'.format(str(e)))
        return None


def lambda_handler(event, context):
    try:
        logger.info('event: {}'.format(event))
        message = event.get('detail')
        life_cycle_hook = message.get('LifecycleHookName')
        auto_scaling_group = message.get('AutoScalingGroupName')
        instance_id = message.get('EC2InstanceId')

        if not all([life_cycle_hook, auto_scaling_group, instance_id]):
            logging.error('No valid message: {}'.format(message))
            return

        if check_document():
            command_id = send_command(instance_id, auto_scaling_group)

            if command_id is not None:

                if check_command(command_id, instance_id):
                    logger.info("Lambda executed correctly")
                else:
                    abandon_lifecycle(life_cycle_hook,
                                      auto_scaling_group,
                                      instance_id)
            else:
                abandon_lifecycle(life_cycle_hook,
                                  auto_scaling_group,
                                  instance_id)
        else:
            abandon_lifecycle(life_cycle_hook, auto_scaling_group, instance_id)

    except Exception as e:
        logger.error('Error: {}'.format(str(e)))
