import boto3
import json
import logging


def get_secret(secret_name, region="us-west-2"):
    """
    Retrieves secret value from a secret in AWS Secrets Manager.

    Parameters:
    - secret_name (str): The name of the secret.
    - region (str): The AWS region where the secret is stored.

    Returns:
    - The value associated with the specified key.
    """

    client = boto3.client(service_name="secretsmanager", region_name=region)

    try:
        secret_response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        logging.warning(f"Error retrieving secret: {e}")
        return None

    if "SecretString" in secret_response:
        secret = json.loads(secret_response["SecretString"])[secret_name]
        return secret
    else:
        logging.warning("Secret is binary or unavailable in string format.")
        return None