import boto3
import base64
import json
from collections import OrderedDict
from chatbot_backend.configs import DYNAMODB_TABLE_NAME, DYNAMODB_PARTITION_KEY, REGION


dynamodb_client = boto3.client(
    service_name='dynamodb',
    region_name=REGION
)


def put_chat_log(user_id, timestamp, chat_log, recommended_items):
    encoded_chat_log = [base64.b64encode(json.dumps(chat).encode('utf-8')) for chat in chat_log]
    dynamodb_client.put_item(
        TableName=DYNAMODB_TABLE_NAME,
        Item={
            DYNAMODB_PARTITION_KEY: {
                "S": f'{user_id}_{timestamp}'
            },
            'chat_log': {
                "BS": list(OrderedDict.fromkeys(encoded_chat_log))
            },
            'recommended_items': {
                "SS": list(set(recommended_items))
            }
        }
    )


def update_chat_log(user_id, timestamp, chat_log, recommended_items):
    encoded_chat_log = [base64.b64encode(json.dumps(chat).encode('utf-8')) for chat in chat_log]
    dynamodb_client.update_item(
        TableName=DYNAMODB_TABLE_NAME,
        Item={
            DYNAMODB_PARTITION_KEY: {
                "S": f'{user_id}_{timestamp}'
            },
            'chat_log': {
                "BS": list(OrderedDict.fromkeys(encoded_chat_log))
            },
            'recommended_items': {
                "SS": list(set(recommended_items))
            }
        }
    )


def get_chat_logs(user_id):
    response = dynamodb_client.scan(
        TableName=DYNAMODB_TABLE_NAME,
        FilterExpression='contains(#pk, :partial)',
        ExpressionAttributeNames={
            '#pk': DYNAMODB_PARTITION_KEY
        },
        ExpressionAttributeValues={
            ':partial': {'S': user_id}
        }
    )

    return response['Items']
