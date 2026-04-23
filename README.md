# HNG14 Stage 2 DevOps — Job Processing Stack

This project is a containerized job processing system made up of four services:

- **Frontend** — Node.js/Express app for submitting jobs and checking job status
- **API** — FastAPI service that creates jobs and stores their status in Redis
- **Worker** — Python worker that picks jobs from Redis and marks them as completed
- **Redis** — shared queue/data store used by the API and worker

## Prerequisites

Install the following on the machine:

- Git
- Docker
- Docker Compose v2

Check that Docker is available:

```bash
docker --version
docker compose version
```

### Clone the repository
```bash
git clone [https://github.com/seyiadisa/hng14-stage2-devops.git](https://github.com/seyiadisa/hng14-stage2-devops.git)
cd hng14-stage2-devops
```

### Create the environment file
Copy the example environment file:

```bash
cp .env.example .env
```

The default `.env.example` values are suitable for local startup:

```env
IMAGE_TAG=latest
APP_NETWORK_NAME=job-app-net

REDIS_IMAGE=redis:7.2-alpine
REDIS_HOST=redis
REDIS_PORT=6379

REDIS_HEALTHCHECK_INTERVAL=10s
REDIS_HEALTHCHECK_TIMEOUT=3s
REDIS_HEALTHCHECK_RETRIES=5
REDIS_HEALTHCHECK_START_PERIOD=5s

API_IMAGE_NAME=job-api
API_PORT=8000
API_HOST_PORT=8000

WORKER_IMAGE_NAME=job-worker

FRONTEND_IMAGE_NAME=job-frontend
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=3000
FRONTEND_HOST_PORT=3000
FRONTEND_API_URL=http://api:8000
```

## Build and start the full stack

```bash
docker compose --env-file .env up -d --build
```

This builds and starts:
- Redis
- API
- Worker
- Frontend

## Check that containers are running

```bash
docker compose --env-file .env ps
```

A successful startup should show all services running. The API, worker, frontend, and Redis containers should be listed as running, and services with healthchecks should eventually show as healthy.

You can also inspect logs:

```bash
docker compose --env-file .env logs -f
```

**Expected useful log signs:**

* **Frontend** should print something like: `Frontend running on http://0.0.0.0:3000`
* **Worker** should log jobs when they are processed: 
    * `Processing job <job_id>`
    * `Done: <job_id>`

## Test the stack manually

### 1. Check the frontend health endpoint
```bash
curl [http://127.0.0.1:3000/health](http://127.0.0.1:3000/health)
```
**Expected response:**
```json
{"status":"ok"}
```

### 2. Check the API health endpoint
```bash
curl [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
```
**Expected response:**
```json
{"status":"ok"}
```

### 3. Submit a job through the frontend
```bash
curl -X POST [http://127.0.0.1:3000/submit](http://127.0.0.1:3000/submit)
```
**Expected response:**
```json
{"job_id":"some-generated-job-id"}
```
*Copy the returned `job_id`.*

### 4. Check job status
Replace `<job_id>` with your copied ID:
```bash
curl [http://127.0.0.1:3000/status/](http://127.0.0.1:3000/status/)<job_id>
```
**Expected response shortly after submission:**
```json
{
  "job_id": "replace-with-your-job-id",
  "status": "completed"
}
```
*The worker simulates job processing and should mark the job as completed.*

## Run the integration test
After the stack is running, run:

```bash
FRONTEND_URL=[http://127.0.0.1:3000](http://127.0.0.1:3000) python scripts/integration_test.py
```

A successful run should look similar to:
```text
Submitted job <job_id>
Job <job_id> status: queued
Job <job_id> status: completed
```

## Stop the stack
```bash
docker compose --env-file .env down
```

To remove volumes as well:
```bash
docker compose --env-file .env down -v
```

## Rebuild from scratch
If you want a clean rebuild:
```bash
docker compose --env-file .env down -v
docker compose --env-file .env build --no-cache
docker compose --env-file .env up -d
```

## Service URLs
When running locally with the default `.env` values:

| Service | URL |
| :--- | :--- |
| **Frontend** | [http://127.0.0.1:3000](http://127.0.0.1:3000) |
| **Frontend health** | [http://127.0.0.1:3000/health](http://127.0.0.1:3000/health) |
| **API** | [http://127.0.0.1:8000](http://127.0.0.1:8000) |
| **API health** | [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) |
| **Redis** | Internal Docker network only |

## Architecture
```text
User / Browser
      |
      v
Frontend service
      |
      v
API service
      |
      v
Redis queue/store
      |
      v
Worker service
```

**Flow:**
1. User submits a job through the frontend.
2. Frontend sends the request to the API.
3. API creates a job record in Redis and pushes the job ID into a Redis queue.
4. Worker pulls the job from Redis.
5. Worker processes the job and updates the job status to completed.
6. User checks the job status through the frontend.

## Troubleshooting

### Port already in use
If port 3000 or 8000 is already in use, change these values in `.env`:
```env
FRONTEND_HOST_PORT=3001
API_HOST_PORT=8001
```
Then restart:
```bash
docker compose --env-file .env down
docker compose --env-file .env up -d
```

### Frontend is not reachable
Check container status:
```bash
docker compose --env-file .env ps
```
Check frontend logs:
```bash
docker compose --env-file .env logs frontend
```

### API is unhealthy
Check API logs:
```bash
docker compose --env-file .env logs api
```
Also confirm Redis is healthy:
```bash
docker compose --env-file .env logs redis
```

### Worker is not processing jobs
Check worker logs:
```bash
docker compose --env-file .env logs worker
```
You should see logs when jobs are picked up and completed.
