import boto3
from time import sleep
from chatbot_backend.configs import PERSONALIZED_RANKING_ARN, USER_PERSONALIZATION_ARN, REGION, \
    DATASET_GROUP_ARN, BEST_SELLERS_ARN

personalize_runtime = boto3.client(
    service_name='personalize-runtime',
    region_name=REGION
)

personalize = boto3.client(
    service_name='personalize',
    region_name=REGION
)


def get_recommendations(user_id: str, filter_arn: str):
    """
    Get recommendations from user-personalize-v2 recipe
    :param user_id: User ID to recommend for
    :param filter_arn: ARN of the filter to use
    :return: list of recommendations
    """
    response = personalize_runtime.get_recommendations(
        campaignArn=USER_PERSONALIZATION_ARN,
        userId=user_id,
        filterArn=filter_arn,
        numResults=500
    )

    return response


def personalized_ranking(user_id: str, product_list: list):
    """
    Rerank a list of similar items with personalized-ranking recipe
    :param user_id: User ID to recommend for
    :param product_list: Product list to rerank
    :return: Reranked list of products in the order of recommendation
    """
    response = personalize_runtime.get_personalized_ranking(
        campaignArn=PERSONALIZED_RANKING_ARN,
        userId=user_id,
        inputList=product_list,
        filterArn='arn:aws:personalize:ap-northeast-2:851725462015:filter/exclude_purchase'
    )

    return response


def get_bestsellers(user_id: str, filter_arn: str):
    response = personalize_runtime.get_recommendations(
        recommenderArn=BEST_SELLERS_ARN,
        userId=user_id,
        filterArn=filter_arn
    )

    return response


def create_filter(filter_name, filter_expression):
    response = personalize.create_filter(
        name=filter_name,
        datasetGroupArn=DATASET_GROUP_ARN,
        filterExpression=filter_expression
    )

    filter_arn = response['filterArn']

    while True:
        filter_response = personalize.describe_filter(filterArn=filter_arn)
        status = filter_response['filter']['status']

        if status == 'ACTIVE': break
        else: sleep(1)

    return filter_arn