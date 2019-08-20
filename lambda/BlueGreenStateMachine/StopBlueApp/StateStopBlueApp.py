# # -*- coding: utf-8 -*-
# import logging
# import boto3
# from botocore.exceptions import ClientError
# # import layer
# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch_all
#
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
#
# patch_all()
#
# asg = boto3.client('autoscaling', region_name='ap-northeast-1')
# ssm = boto3.client('ssm', region_name='ap-northeast-1')
#
#
# # @xray_recorder.capture('## lambda_handler')
# def lambda_handler(event, context):
#     try:
#         logger.info('event: {}'.format(event))
#         blue_asg_name = event['blue']['asg_name']
#         result = stop_mq_agent(blue_asg_name)
#         result = True
#         return result
#
#     except ClientError as e:
#         logger.exception('ASG Exception: {}'.format(e))
#         raise e
#
#     except Exception as e:
#         logger.exception('ASG Exception: {}'.format(e))
#         raise e
#
#
# def stop_mq_agent(blue_asg_name):
#     try:
#         instances = get_asg_instances(blue_asg_name)
#
#         commands = stop_mq_shell_script()
#
#         ssm.send_command(
#             InstanceIds=instances,
#             DocumentName='AWS-RunShellScript',
#             Parameters={
#                     "commands": commands,
#                     "executionTimeout": ["3600"]
#                 }
#         )
#
#     except Exception as e:
#         raise e
#
#
# def stop_mq_shell_script():
#     script = ['systemctl stop httpd.service']
#     return script
#
#
# # TODO  停止したかどうかは別途SFNの関数で行う
# def is_active():
#     script = [
#         'isAlive="ps aux | grep http[d] | wc -l"',
#         'if [ $isAlive = 1 ]; then',
#         ' echo "httpd is running."',
#         'else',
#         ' echo "httpd is stop."',
#         'fi',
#     ]
#     return script
#
#
# def get_asg_instances(blue_asg_name):
#
#     # ASG Parameters
#     asg_info = asg.describe_auto_scaling_groups(
#         AutoScalingGroupNames=[blue_asg_name])
#     instances = asg_info['AutoScalingGroups'][0]['Instances']
#     instance_id_list = [i['InstanceId'] for i in instances]
#
#     return instance_id_list
