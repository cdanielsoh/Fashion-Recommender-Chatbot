import boto3
from botocore.exceptions import ClientError
from chatbot_backend.configs import BEDROCK_REGION, CHAT_MODEL_ID, FILTER_FLOW, FILTER_FLOW_ALIAS, FEATURE_MODEL_ID
from chatbot_backend.chatbot_bedrock.prompts import CATEGORICAL_METADATA
import json


bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=BEDROCK_REGION
)

bedrock_agent = boto3.client(
    service_name='bedrock-agent-runtime',
    region_name=BEDROCK_REGION
)


def invoke_stream_with_text(prompt, user_input, model=CHAT_MODEL_ID):

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"System instruction: {prompt}\n\nUser: {user_input}"
                    }
                ]
            }
        ]
    }

    return invoke_stream(request_body, model)


def invoke_with_text(prompt, user_input):
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"System instruction: {prompt}\n\nUser: {user_input}"
                    }
                ]
            }
        ]
    }

    response = bedrock.invoke_model(
            modelId=CHAT_MODEL_ID,
            body=json.dumps(request_body)
        )

    response_body = json.loads(response["body"].read())

    return response_body["content"][0]["text"]


def get_filter_information(prompt, user_input, session_context):

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"System instruction: {prompt}\n\nUser: {user_input}\n\nCategorical metadata: {CATEGORICAL_METADATA}\n\nChat history context: {session_context}"
                    }
                ]
            }
        ]
    }

    return invoke_stream(request_body)


def generate_recommendation(prompt, user_preferences, image, features):
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{prompt}\n\nUser Preferences: {json.dumps(user_preferences)}\n\nProduct features: {features}"
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image
                        }
                    }
                ]
            }
        ],
        "temperature": 0.5,
        "top_p": 0.999,
        "top_k": 250,
    }

    return invoke_stream(request_body, FEATURE_MODEL_ID)


def describe_image(prompt, image):
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image
                        }
                    }
                ]
            }
        ],
        "temperature": 0.5,
        "top_p": 0.999,
        "top_k": 250,
        "stop_sequences": ["\n\nHuman:"],
    }

    return invoke_stream(request_body)


def invoke_stream(payload, model=CHAT_MODEL_ID):

    try:
        response = bedrock.invoke_model_with_response_stream(
            modelId=model,
            body=json.dumps(payload)
        )

        for event in response.get('body'):
            chunk = json.loads(event['chunk']['bytes'])
            if 'delta' in chunk:
                yield chunk['delta'].get('text', '')

    except ClientError as e:
        return f"An error occurred: {str(e)}"


def invoke_interaction_flow(user_input, current_filter):
    payload = {
            "user_input": user_input,
            "current_filter": current_filter,
            "categorical_metadata": json.loads(CATEGORICAL_METADATA)
        }

    response = bedrock_agent.invoke_flow(
        flowIdentifier=FILTER_FLOW,
        flowAliasIdentifier=FILTER_FLOW_ALIAS,
        inputs=[
            {
                'content': {
                    'document': payload
                },
                'nodeName': 'FlowInputNode',
                'nodeOutputName': 'document'
            }
        ]
    )

    return response['responseStream']
