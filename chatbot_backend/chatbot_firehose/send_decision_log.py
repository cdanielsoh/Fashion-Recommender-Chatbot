import boto3
import json


firehose_client = boto3.client(service_name='firehose', region_name='ap-northeast-2')


def send_record_to_firehose(payload):
    try:
        response = firehose_client.put_record(
            DeliveryStreamName='abp3-firehose',
            Record={'Data': json.dumps(payload, ensure_ascii=False) + '\n'}
        )
        return response['RecordId']
    except Exception as e:
        print(f"Error sending record: {str(e)}")
        raise
