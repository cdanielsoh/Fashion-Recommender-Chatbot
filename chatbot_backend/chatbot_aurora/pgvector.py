import psycopg
from psycopg.rows import dict_row
from contextlib import contextmanager
import json
import boto3
from botocore.exceptions import ClientError
from chatbot_backend.configs import REGION, AURORA_WRITER_ENDPOINT, AURORA_PORT, AURORA_SECRET_NAME


def get_secret(secret_name=AURORA_SECRET_NAME):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=REGION
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']

    return json.loads(secret)


def get_connection(dbname: str):
    secret = get_secret()

    conn_string = f"""
        dbname={dbname} 
        user={secret['username']} 
        password={secret['password']} 
        host={AURORA_WRITER_ENDPOINT} 
        port={AURORA_PORT}
    """

    return psycopg.connect(conn_string, autocommit=True)


@contextmanager
def get_cursor(conn):
    with conn.cursor(row_factory=dict_row) as cursor:
        yield cursor


def create_vector_extension(conn):
    with get_cursor(conn) as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def create_database(conn, db_name):
    with get_cursor(conn) as cursor:
        cursor.execute(f"CREATE DATABASE {db_name}")


def create_table(conn, table_name, columns):
    """Create a new table in the current database."""
    with get_cursor(conn) as cursor:
        columns_str = ", ".join(columns)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} 
            ({columns_str})
        """)


def insert_embedding(conn, table_name, item_id, embedding):
    """Insert an embedding into a table."""
    with get_cursor(conn) as cursor:
        cursor.execute(f"INSERT INTO {table_name} (id, embedding) VALUES (%s, %s);",
                       (item_id, embedding))


def knn_search(conn, table_name, query_embedding, k):
    """Perform a K-nearest neighbors search."""
    with get_cursor(conn) as cursor:
        cursor.execute(f"""
            SELECT id, embedding <-> %s::vector AS distance
            FROM {table_name}
            ORDER BY distance
            LIMIT %s;
        """, (query_embedding, k))
        return cursor.fetchall()


def get_user_interacted_items(conn, user_id, num_items):
    """Get items that a user has interacted with."""
    with get_cursor(conn) as cursor:
        cursor.execute("""
            SELECT DISTINCT ON (i.item_id) i.*
            FROM items i
            JOIN interactions intr ON i.item_id = intr.item_id
            WHERE intr.user_id = %s
            AND i.season IS NOT NULL
            AND i.season != 'NaN'
            ORDER BY i.item_id, intr.timestamp DESC
            LIMIT %b;
        """, (user_id, num_items))
        return cursor.fetchall()


def get_item_list_features(conn, item_list):
    item_tuple = tuple(item_list)
    if item_tuple:
        with get_cursor(conn) as cursor:
            placeholders = ",".join(['%s'] * len(item_tuple))
            cursor.execute(f"""
                SELECT *
                FROM items
                WHERE item_id IN ({placeholders})
            """, item_tuple)

            item_id_to_details = {item['item_id']: {k: v for k, v in item.items() if k != 'item_id'} \
                                  for item in cursor.fetchall()}

            return item_id_to_details

    else:
        return []



def execute_query(conn, query):
    with get_cursor(conn) as cursor:
        cursor.execute(query)
        return cursor.fetchall()