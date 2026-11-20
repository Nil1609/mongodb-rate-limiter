
import os
from typing import Optional
from datetime import datetime, timezone

from dotenv import load_dotenv

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError, DuplicateKeyError

from fastapi import (
    FastAPI,
    Request,
    HTTPException,
    Header
)

# ==================================================
# 1. CONFIGURATION
# ==================================================

load_dotenv()

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017/"
)

DATABASE_NAME = os.getenv(
    "DATABASE_NAME",
    "rate_limiter_db"
)

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "5"))

WINDOW_SECONDS = int(
    os.getenv("WINDOW_SECONDS", "60")
)


# ==================================================
# 2. MONGODB CONNECTION
# ==================================================

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

db = client[DATABASE_NAME]

collection = db["rate_limits"]


# ==================================================
# 3. FASTAPI APPLICATION
# ==================================================

app = FastAPI(
    title="MongoDB Rate Limiter",
    description=(
        "API Rate Limiter using MongoDB "
        "and Fixed Window Counter Algorithm"
    ),
    version="1.0.0"
)


# ==================================================
# 4. RATE LIMITING FUNCTION
# ==================================================

def check_rate_limit(user_id: str):

    # Step 1: Create user document if not present

    try:

        collection.update_one(
            {"_id": user_id},

            {
                "$setOnInsert": {
                    "request_count": 0,
                    "window_start": datetime.now(timezone.utc),
                    "last_request": None,
                    "limit": RATE_LIMIT,
                    "window_duration": WINDOW_SECONDS
                }
            },

            upsert=True
        )

    except DuplicateKeyError:
        # Another concurrent request may have
        # created the same user document.
        pass

    # Step 2: Atomically check window expiration
    # and increment or reset the counter.

    updated = collection.find_one_and_update(

        {"_id": user_id},

        [
            {
                "$set": {

                    "_expired": {
                        "$lte": [

                            {
                                "$add": [
                                    "$window_start",

                                    {
                                        "$multiply": [
                                            "$window_duration",
                                            1000
                                        ]
                                    }
                                ]
                            },

                            "$$NOW"
                        ]
                    }
                }
            },

            {
                "$set": {

                    "request_count": {
                        "$cond": [
                            "$_expired",
                            1,
                            {"$add": ["$request_count", 1]}
                        ]
                    },

                    "window_start": {
                        "$cond": [
                            "$_expired",
                            "$$NOW",
                            "$window_start"
                        ]
                    },

                    "last_request": "$$NOW"
                }
            },

            {
                "$unset": "_expired"
            }
        ],

        return_document=ReturnDocument.AFTER
    )

    # Step 3: Determine request permission

    allowed = (
        updated["request_count"] <= RATE_LIMIT
    )

    # Step 4: Calculate remaining window time

    window_start = updated["window_start"]

    if window_start.tzinfo is None:

        window_start = window_start.replace(
            tzinfo=timezone.utc
        )

    elapsed = (
        datetime.now(timezone.utc) - window_start
    ).total_seconds()

    retry_after = max(
        1,
        int(WINDOW_SECONDS - elapsed)
    )

    # Step 5: Return rate-limit information

    return {

        "user_id": user_id,

        "allowed": allowed,

        "request_count": updated["request_count"],

        "limit": RATE_LIMIT,

        "remaining": max(
            0,
            RATE_LIMIT - updated["request_count"]
        ),

        "retry_after": retry_after
    }


# ==================================================
# 5. HOME ENDPOINT
# ==================================================

@app.get("/")
def home():

    return {

        "message": "MongoDB Rate Limiter is running",

        "database": DATABASE_NAME,

        "algorithm": "Fixed Window Counter",

        "rate_limit": RATE_LIMIT,

        "window_seconds": WINDOW_SECONDS
    }


# ==================================================
# 6. PROTECTED RESOURCE ENDPOINT
# ==================================================

@app.get("/resource")
def access_resource(

    request: Request,

    x_api_key: Optional[str] = Header(
        default=None,
        alias="X-API-Key"
    )

):

    # Step 1: Identify client

    user_id = (
        x_api_key
        or (
            request.client.host
            if request.client
            else "unknown"
        )
    )

    # Step 2: Apply rate limiter

    try:

        result = check_rate_limit(user_id)

    except PyMongoError:

        raise HTTPException(
            status_code=503,
            detail="Rate limiter database unavailable"
        )

    # Step 3: Prepare response headers

    headers = {

        "X-RateLimit-Limit": str(
            result["limit"]
        ),

        "X-RateLimit-Remaining": str(
            result["remaining"]
        )
    }

    # Step 4: Reject excessive requests

    if not result["allowed"]:

        headers["Retry-After"] = str(
            result["retry_after"]
        )

        raise HTTPException(

            status_code=429,

            detail="Rate limit exceeded. Try again later.",

            headers=headers
        )

    # Step 5: Allow request

    from fastapi.responses import JSONResponse

    return JSONResponse(

        status_code=200,

        content={

            "message": "Request successful",

            "user_id": result["user_id"],

            "request_count": result["request_count"],

            "limit": result["limit"],

            "remaining": result["remaining"]
        },

        headers=headers
    )


# ==================================================
# 7. USER STATISTICS ENDPOINT
# ==================================================

@app.get("/stats/{user_id}")
def get_user_stats(user_id: str):

    try:

        record = collection.find_one(
            {"_id": user_id},

            {
                "_id": 1,
                "request_count": 1,
                "window_start": 1,
                "last_request": 1,
                "limit": 1,
                "window_duration": 1
            }
        )

    except PyMongoError:

        raise HTTPException(
            status_code=503,
            detail="Database unavailable"
        )

    if not record:

        raise HTTPException(
            status_code=404,
            detail="User record not found"
        )

    record["_id"] = str(record["_id"])

    return record


# ==================================================
# 8. HEALTH CHECK ENDPOINT
# ==================================================

@app.get("/health")
def health():

    try:

        client.admin.command("ping")

        return {

            "status": "healthy",

            "database": "MongoDB",

            "connection": "successful"
        }

    except PyMongoError:

        raise HTTPException(

            status_code=503,

            detail="MongoDB connection unavailable"
        )


# ==================================================
# 9. DATABASE INFORMATION
# ==================================================

@app.get("/database")
def database_info():

    try:

        total_users = collection.count_documents({})

        return {

            "database": DATABASE_NAME,

            "collection": "rate_limits",

            "total_users": total_users,

            "status": "connected"
        }

    except PyMongoError:

        raise HTTPException(
            status_code=503,
            detail="Database unavailable"
        )
