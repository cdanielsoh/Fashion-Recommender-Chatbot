import json
import pandas as pd
from chatbot_backend.chatbot_firehose.send_decision_log import send_record_to_firehose
from chatbot_backend.chatbot_personalize.recommend import personalized_ranking, get_recommendations, \
    create_filter, get_bestsellers
from chatbot_backend.chatbot_bedrock.image import embed_image
from chatbot_backend.chatbot_aurora.pgvector import get_connection, get_user_interacted_items, \
    knn_search, execute_query
from chatbot_backend.configs import AURORA_VECTOR_DB_NAME, AURORA_VECTOR_DB_TABLE_NAME, \
    AURORA_CUSTOMER_DB_NAME, S3_IMAGES_BUCKET, FILTER_ARN_DOMAIN
from chatbot_backend.chatbot_s3.s3 import read_image_from_s3
from chatbot_backend.chatbot_dynamodb.chatbot_logs import put_chat_log, get_chat_logs, update_chat_log
import base64
from io import BytesIO
from datetime import datetime
from bing_image_downloader import downloader
from PIL import Image
import os
import shutil


def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def knn_search_with_image(image, k=20)->list:

    image_embedding = embed_image(encode_image(image))

    vectordb_conn = get_connection(AURORA_VECTOR_DB_NAME)

    knn_list = knn_search(vectordb_conn, AURORA_VECTOR_DB_TABLE_NAME, image_embedding, k)

    return knn_list


def rerank_personalized_ranking(user_id, image_list)->list:
    """
    Generate personalized recommendation based on similarity to a given image.
    Perform k-NN search on PGVector to retrieve list of images
    Rerank using personalized_ranking in Amazon Personalize
    :param user_id: user ID to personalize for
    :param image_list: input image list to rerank
    :return: reranked list of item IDs
    """
    image_ids = [str(row["id"]) for row in image_list]

    response = personalized_ranking(user_id, image_ids)

    ranked_items = response['personalizedRanking']

    return [item['itemId'] for item in ranked_items]


def personalized_recommend(user_id, filters)->list:
    """
    Generate personalized recommendation based on user text inputs.
    Filters are gathered using user interactions
    :param user_id: user ID to personalize for
    :param filters: filters to apply to personalize
    :return: list of item IDs
    """

    filter_arn = construct_personalize_filter(user_id, filters)

    response = get_recommendations(user_id, filter_arn)

    ranked_items = response['itemList']

    return [item['itemId'] for item in ranked_items]


def personalized_recommend_pg(user_id, filters)->list:
    """
    Query items using a filter on PostgreSQL.
    Then rerank items using Personalize's personalized_ranking recipe.
    :param user_id: user ID to personalize for
    :param filters: filters to apply to personalize
    :return: list of item IDs
    """

    image_list = construct_pg_filter(filters)

    image_ids = [str(row["item_id"]) for row in image_list[:100]]

    response = personalized_ranking(user_id, image_ids)

    ranked_items = response['personalizedRanking']

    return [item['itemId'] for item in ranked_items]


def personalized_recommend_pg2(user_id, filters)->list:
    """
    Query items using a category_l2 filter on Personalize.
    :param user_id: user ID to personalize for
    :param filters: filters to apply to personalize
    :return: list of item IDs
    """

    filter_arn = get_filter_arn(filters)

    response = get_recommendations(user_id, filter_arn)

    item_list = [item['itemId'] for item in response['itemList']]

    filtered_items = [str(row["item_id"]) for row in construct_pg_filter(filters)]

    return list(set(item_list) & set(filtered_items)) if filtered_items else item_list


def best_sellers_recommend(user_id, filters):

    filter_arn = get_filter_arn(filters)

    response = get_bestsellers(user_id, filter_arn)

    ranked_items = response['itemList']

    return [item['itemId'] for item in ranked_items]


def best_sellers_recommend2(user_id, filters):
    filter_arn = get_filter_arn(filters)

    response = get_bestsellers(user_id, filter_arn)

    item_list = [item['itemId'] for item in response['itemList']]

    filtered_items = [str(row["item_id"]) for row in construct_pg_filter(filters)]

    return list(set(item_list) & set(filtered_items)) if filtered_items else item_list


def rank_user_features(user_id):
    past_items = get_user_interacted_items(get_connection(AURORA_CUSTOMER_DB_NAME), user_id, 500)
    items_df = pd.DataFrame(past_items)
    features_to_count = ['color', 'graphical_appearance', 'pattern', 'material', 'style', 'collar',
                         'sleeve', 'season', 'fit', 'length', 'closuretype', 'skirttype']
    ranked_features = {
        feature : items_df[feature].value_counts().to_dict() for feature in features_to_count
    }
    ranked_features['price'] = (items_df['price'].min(), items_df['price'].max())
    return ranked_features


def get_item_images(item_list)->dict:
    encoded_item_images = {}
    for item_key in item_list:
        s3_key = f'0{item_key}.jpg'

        encoded_item_images[item_key] = read_image_from_s3(S3_IMAGES_BUCKET,s3_key)

    return encoded_item_images


def retrieve_past_recommendations(user_id):
    chat_logs = get_chat_logs(user_id)
    recommended_items = {}
    for chat_log in chat_logs:
        tstamp = datetime.fromtimestamp(int(chat_log['userID_timestamp']['S'].split('_')[1]))
        recommended_items[tstamp] = chat_log['recommended_items']['SS']
    return recommended_items


def retrieve_past_user_chat_log(user_id):
    chat_logs = get_chat_logs(user_id)
    past_user_chat = []
    for chat_log in chat_logs:
        chats = chat_log["chat_log"]["BS"]
        for chat in chats:
            chat_json = json.loads(base64.b64decode(chat).decode('utf-8'))
            if chat_json["role"] == "user":

                past_user_chat.append(chat_json["message"])

    return past_user_chat


def save_chat_logs(user_id, tstamp, chat_log, recommended_items):
    try:
        put_chat_log(user_id, tstamp, chat_log, recommended_items)

    except:
        update_chat_log(user_id, tstamp, chat_log, recommended_items)


def get_users():
    query = """
        SELECT user_id, COUNT(*) as buy_count
        FROM interactions
        WHERE event_type = 'purchased'
        GROUP BY user_id
        HAVING COUNT(*) > 500
        ORDER BY buy_count DESC;
    """
    all_users = execute_query(get_connection(AURORA_CUSTOMER_DB_NAME), query)
    all_users_df = pd.DataFrame(all_users)

    return all_users_df


def get_product_desc(item_id):
    query = f"""
        SELECT product_desc
        FROM items
        WHERE item_id = {item_id} 
    """

    product_desc = execute_query(get_connection(AURORA_CUSTOMER_DB_NAME), query)

    return product_desc[0]["product_desc"]


def construct_pg_filter(filters):
    try:
        query_parts = []
        for column, values in filters.items():
            if column == 'price':
                query_parts.append(f"{column} < {values[1]}")
            else:
                formatted_values = ', '.join([f"'{value}'" for value in values])
                query_parts.append(f"{column.lower()} IN ({formatted_values})")
        query = ' AND '.join(query_parts)

        query = f"SELECT item_id FROM items WHERE {query};"

        filtered_items = execute_query(get_connection(AURORA_CUSTOMER_DB_NAME), query)

        return filtered_items

    except:
        return []


def construct_personalize_filter(user_id, filters):
    filter_category = 'Items.'
    filter_expression = 'INCLUDE ItemID WHERE '
    count = 0

    for category, values in filters.items():
        joined_values = ','.join([f'"{value}"' for value in values])
        if count > 0: filter_expression += 'AND '
        filter_expression += f'{filter_category}{category} IN ({joined_values.lower()}) '
        count += 1

    filter_expression = 'EXCLUDE ItemID WHERE INTERACTIONS.event_type IN ("Purchase")|' + filter_expression

    filter_name = f'{user_id[:10]}-{int(datetime.now().timestamp())}'

    return create_filter(filter_name, filter_expression)


def search_web_image(keywords, limit=1):
    temp_dir = "temp_image_download"
    downloader.download(keywords, limit=limit, output_dir=temp_dir, verbose=False,
                        adult_filter_off=True, force_replace=False, timeout=60)

    images = []
    query_dir = os.path.join(temp_dir, keywords)
    from time import sleep
    while not os.listdir(query_dir):
        sleep(1)
    file_path = os.path.join(query_dir, os.listdir(query_dir).pop())

    with Image.open(file_path) as img:
        img_copy = img.copy()
        images.append(img_copy)

    shutil.rmtree(temp_dir)

    return images.pop()


def get_filter_arn(filters):
    if "CATEGORY_L2" in filters:
        category = filters["CATEGORY_L2"][0].replace(" ", "").replace("/", "")
        return f"{FILTER_ARN_DOMAIN}/{category}"
    else:
        return f"{FILTER_ARN_DOMAIN}/exclude_purchase"


def send_chatbot_decision(data):
    payload = {
        'user_prompt': data['user_prompt'],
        'llm_decision': data['next_action'],
        'decision_score': data['score'],
    }

    send_record_to_firehose(payload)
