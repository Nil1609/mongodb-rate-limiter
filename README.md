# MongoDB-Based API Rate Limiter

A backend API rate-limiting system built using Python, FastAPI, and MongoDB. It uses the **Fixed Window Counter Algorithm** to control the number of requests made by individual users within a specified time interval.

## Project Overview

The application restricts excessive API requests by maintaining a separate request counter for each user in MongoDB.

When a user exceeds the configured request limit, the API returns an HTTP `429 Too Many Requests` response.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| FastAPI | REST API development |
| MongoDB | Document database |
| PyMongo | MongoDB connectivity |
| Uvicorn | ASGI server |
| Python-dotenv | Environment configuration |

## Rate Limiting Algorithm

**Fixed Window Counter**

| Parameter | Value |
|---|---|
| Maximum requests | 5 |
| Time window | 60 seconds |
| Window type | Per-user fixed window |
| Exceeded response | HTTP 429 |

### Working Principle

1. Identify the user using their API key.
2. Retrieve or create the user's MongoDB document.
3. Check whether the current time window has expired.
4. Reset the counter if the window has expired.
5. Increment the request counter atomically.
6. Allow requests within the configured limit.
7. Reject requests exceeding the limit with HTTP 429.

## MongoDB Data Model

**Database:** `rate_limiter_db`

**Collection:** `rate_limits`

Each document stores:

| Field | Description |
|---|---|
| `_id` | Unique user identifier |
| `request_count` | Number of requests in the current window |
| `window_start` | Start time of the current window |
| `last_request` | Timestamp of the latest request |
| `limit` | Maximum permitted requests |
| `window_duration` | Duration of the window in seconds |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Application information |
| GET | `/resource` | Rate-limited resource |
| GET | `/stats/{user_id}` | User request statistics |
| GET | `/health` | MongoDB health check |
| GET | `/database` | Database information |

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/mongodb-rate-limiter.git
cd mongodb-rate-limiter
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
MONGO_URI=mongodb://localhost:27017/
DATABASE_NAME=rate_limiter_db
RATE_LIMIT=5
WINDOW_SECONDS=60
```

Make sure MongoDB is running locally.

### 5. Start the application

```bash
uvicorn main:app --reload
```

### 6. Access API documentation

Open:

http://127.0.0.1:8000/docs

## Testing

The implementation has been tested for:

- Successful requests within the configured limit.
- HTTP 429 responses after exceeding the limit.
- Independent counters for different users.
- Counter reset after the fixed window expires.
- MongoDB document persistence.

## Project Structure

```text
mongo-rate-limiter/
├── main.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
└── venv/
```

## Future Enhancements

- Implement Sliding Window Counter.
- Add API key authentication.
- Introduce configurable limits for different users.
- Add monitoring and analytics.
- Implement distributed rate limiting.

## Author

Niladri Sekhar Dutta

## GitHub Repository

Add your repository URL here.