import socket
import boto3
import json
from kafka import KafkaProducer
from chatbot_backend.configs import CLUSTER_ARN, REGION
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider


class MSKTokenProvider():
    def token(self):
        token, _ = MSKAuthTokenProvider.generate_auth_token('ap-northeast-2')
        return token


tp = MSKTokenProvider()

msk_client = boto3.client(
    service_name='kafka',
    region_name=REGION
)
response = msk_client.get_bootstrap_brokers(
    ClusterArn=CLUSTER_ARN
)

bootstrap_servers = response["BootstrapBrokerStringSaslIam"]


def start_producer():
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        security_protocol='SASL_SSL',
        sasl_mechanism='OAUTHBEARER',
        sasl_oauth_token_provider=tp,
        client_id=socket.gethostname(),
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )


def submit_order(user_id, items: list, event_type):
    producer = start_producer()
    topic = 'orders'
    items = [item["item_id"] for item in items]
    message = {
        'user_id': user_id,
        'items': items,
        'event_type': event_type
    }
    producer.send(topic, value=message)
    producer.close()
    return 0
