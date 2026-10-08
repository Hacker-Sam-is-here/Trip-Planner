"""Setup script to create DynamoDB table for PATHwise route caching."""

import logging
import os
import sys
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_cache_table() -> None:
    """Create DynamoDB table with TTL enabled and PAY_PER_REQUEST billing."""
    table_name = os.getenv("DYNAMO_TABLE", "pathwise-route-cache").strip()
    dynamodb = boto3.client("dynamodb")

    try:
        logger.info("Creating DynamoDB table: %s", table_name)
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "cache_key", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "cache_key", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
        logger.info("Table %s created successfully.", table_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceInUseException":
            logger.info("Table %s already exists.", table_name)
        else:
            logger.error("Failed to create table: %s", exc)
            raise

    try:
        logger.info("Enabling TTL attribute 'expires_at' on %s", table_name)
        dynamodb.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                "Enabled": True,
                "AttributeName": "expires_at",
            },
        )
        logger.info("TTL enabled successfully.")
    except ClientError as exc:
        logger.warning("Could not configure TTL (it may already be enabled): %s", exc)


if __name__ == "__main__":
    try:
        create_cache_table()
    except Exception as err:
        logger.error("Error setting up DynamoDB: %err", err)
        sys.exit(1)
