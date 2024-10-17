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

    Raises:
    - Exception: If the secret cannot be retrieved or is not available.
    """

    client = boto3.client(service_name="secretsmanager", region_name=region)

    try:
        secret_response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        logging.error(f"Failed to retrieve secret: {secret_name}. Error details: {e}")
        raise Exception(f"Failed to retrieve secret: {secret_name}. Error details: {e}")

    if "SecretString" in secret_response:
        secret = json.loads(secret_response["SecretString"])[secret_name]
        return secret
    else:
        logging.error(f"Secret {secret_name} is not available in string format.")
        raise Exception(f"Secret {secret_name} is not available in string format.")
