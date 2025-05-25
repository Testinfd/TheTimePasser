# Clone Bot

from pymongo import MongoClient
import motor.motor_asyncio
import ssl

def get_mongo_client(uri):
    """
    Create a MongoDB client with proper TLS/SSL settings.
    This resolves the SSL handshake failures with MongoDB Atlas.
    """
    if not uri:
        return None
    
    # Connect with modern TLS/SSL options
    return MongoClient(
        uri,
        tls=True,
        tlsAllowInvalidCertificates=True
    )

def get_async_mongo_client(uri):
    """
    Create an asynchronous MongoDB client with proper TLS/SSL settings.
    For Motor AsyncIOMotorClient connections.
    """
    if not uri:
        return None
    
    # Connect with modern TLS/SSL options
    return motor.motor_asyncio.AsyncIOMotorClient(
        uri,
        tls=True,
        tlsAllowInvalidCertificates=True
    ) 