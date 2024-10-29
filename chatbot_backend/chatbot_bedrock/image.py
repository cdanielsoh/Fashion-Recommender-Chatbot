import base64
import json
import boto3
from chatbot_backend.configs import BEDROCK_REGION, EMBEDDING_MODEL_ID, FEATURE_MODEL_ID
from chatbot_backend.chatbot_bedrock.prompts import FEATURES_FROM_IMAGES_PROMPT


bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=BEDROCK_REGION
)


def embed_image(encoded_image_bytes):
    """
    Embed image using Amazon Bedrock with EMBEDDING_MODEL_ID
    :param encoded_image_bytes: Image to convert to embeddings in byte format. Already base64 encoded.
    :return: Embeddings of the given image
    """
    body = json.dumps({
        'inputImage': encoded_image_bytes
    })

    response = bedrock.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        contentType='application/json',
        accept='application/json',
        body=body
    )

    response_body = json.loads(response['body'].read())

    return response_body['embedding']


def get_image_features(image_bytes):
    """
    Retrieve feature of an image in json format.
    :param image_bytes: Image to retrieve features from in byte format
    :return: features
    :type: json
    """
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_bytes
                        }
                    },
                    {
                        "type": "text",
                        "text": FEATURES_FROM_IMAGES_PROMPT
                    }
                ]
            }
        ]
    })

    features = bedrock.invoke_model(
        body=body,
        modelId=FEATURE_MODEL_ID
    )

    return features
