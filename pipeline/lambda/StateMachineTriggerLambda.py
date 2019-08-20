# -*- coding: utf-8 -*-
import os
import boto3
import logging
from datetime import datetime
import zipfile
import io
# from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
patch_all()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sfn = boto3.client('stepfunctions')
s3 = boto3.client('s3')
codepipeline = boto3.client('codepipeline')

SFN_ARN = os.environ['stateMachineArn']
input_json_file_name = 'state_machine_input.json'


def extract_parameters_codepipeline_job(event):
    _job = event.get('CodePipeline.job')
    job_id = _job.get('id')

    try:
        _input_location = _job\
            .get('data')\
            .get('inputArtifacts')[0]\
            .get('location')

        logger.info('_input_location: {}'.format(_input_location))

        # user_params = json.loads(_configuration.get('UserParameters'))
        # bucket = user_params.get('s3Bucket')
        # sfn_input_file = user_params.get('stateMachineFile')

        bucket_name = _input_location\
            .get('s3Location')\
            .get('bucketName')

        object_key = _input_location\
            .get('s3Location')\
            .get('objectKey')

        logger.info('bucket_name: {}, object_key: {}'
                    .format(bucket_name, object_key))
        return dict(job_id=job_id,
                    bucket_name=bucket_name,
                    object_key=object_key)
    except Exception as e:
        logger.error('Error: {}'.format(str(e)))
        raise


def get_input_artifacts(params):
    try:
        zipped_content_as_bytes = s3.get_object(
            Bucket=params.get('bucket_name'),
            Key=params.get('object_key')
        )['Body'].read()

        z = zipfile.ZipFile(io.BytesIO(zipped_content_as_bytes), 'r')
        # files = z.namelist()
        content_json = z.open(input_json_file_name).read().decode('utf-8')
        z.close()
        logger.info('sfn_input_json: {}'.format(content_json))
        return content_json
    except Exception as e:
        logger.error('Error: {}'.format(str(e)))
        raise


def lambda_handler(event, context):
    date_now = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    logger.info('SNF_ARN: {}'.format(SFN_ARN))
    logger.info('event: {}'.format(event))
    params = extract_parameters_codepipeline_job(event)

    try:
        content_json = get_input_artifacts(params)
        response = sfn.start_execution(
            stateMachineArn=SFN_ARN,
            name=date_now,
            input=content_json
        )
        logger.info(response)
        codepipeline.put_job_success_result(jobId=params.get('job_id'))

    except Exception as e:
        logger.error('Error: {}'.format(str(e)))
        codepipeline.put_job_failure_result(jobId=params.get('job_id'),
                                            failureDetails={
                                                'message': str(e),
                                                'type': 'JobFailed'
                                            })
