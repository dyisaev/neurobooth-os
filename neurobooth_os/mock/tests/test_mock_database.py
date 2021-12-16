import psycopg2
from sshtunnel import SSHTunnelForwarder

from neurobooth_os.mock import insert_mock_rows, delete_mock_rows
from neurobooth_os.secrets_info import secrets


with psycopg2.connect(database='neurobooth_mockup2',
                        user='neuroboother',
                        password='neuroboothjazz',                              
                        host='localhost',
                        port=5432) as conn_mock:
    delete_mock_rows(conn_mock)
    insert_mock_rows(conn_mock)
    delete_mock_rows(conn_mock)
