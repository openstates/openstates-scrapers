import boto3
import json
import logging


class SecretRetrievalError(Exception):
    def __init__(self, message, secret_name=None, original_exception=None):
        full_message = (
            f"{message}. Secret: {secret_name}. Details: {original_exception}"
            if original_exception
            else message
        )
        super().__init__(full_message)

        logging.error(full_message)
        self.secret_name = secret_name
        self.original_exception = original_exception


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
        raise SecretRetrievalError("Error retrieving secret", secret_name, e)

    if "SecretString" in secret_response:
        try:
            secret = json.loads(secret_response["SecretString"])[secret_name]
            return secret
        except KeyError as ke:
            raise SecretRetrievalError(
                "The key was not found in the secret", secret_name, ke
            )
    else:
        raise SecretRetrievalError(
            "Secret is binary or unavailable in string format", secret_name
        )
