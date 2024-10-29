import base64
import io
import pandas as pd
import boto3
from PIL import Image
from chatbot_backend.configs import REGION

s3_client = boto3.client(
    service_name='s3',
    region_name=REGION
)

def read_csv_from_s3(bucket_name, file_key):
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content = response['Body'].read().decode('utf-8')

    df = pd.read_csv(io.StringIO(csv_content))

    return df


def read_image_from_s3(bucket_name, file_key):
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    image_content = response['Body'].read()

    with Image.open(io.BytesIO(image_content)) as img:
        byte_arr = io.BytesIO()
        img.save(byte_arr, format='JPEG')
        image_bytes = byte_arr.getvalue()

    return base64.b64encode(image_bytes).decode('utf-8')
