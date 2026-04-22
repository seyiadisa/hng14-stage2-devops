# Fixes

## `api/main.py` line 8

```python
r = redis.Redis(host="localhost", port=6379)
```

### Problem

The API was hardcoded to connect to Redis on `localhost:6379`. That works only when Redis is running on the same machine and the process is not containerized. Inside Docker Compose, `localhost` would point to the API container itself, not the Redis service.

### Solution

I replaced the hardcoded Redis connection with environment-driven settings so the API can run both locally and in containers.

```python
def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )
```

## `api/main.py` lines 13-14

```python
r.lpush("job", job_id)
r.hset(f"job:{job_id}", "status", "queued")
```

### Problem

The API queued the job before saving its status. That creates a race condition: the worker could pick up and complete the job immediately, then the API would overwrite the final `completed` state back to `queued`.

### Solution

I reversed the order so the initial state is written first, then the job is pushed to the queue.

```python
r.hset(f"job:{job_id}", mapping={"status": "queued"})
r.lpush("job", job_id)
```

## `api/main.py` lines 19-21

```python
status = r.hget(f"job:{job_id}", "status")
if not status:
    return {"error": "not found"}
```

### Problem

When a job did not exist, the API still returned HTTP 200 with a JSON error message. That is misleading for clients and makes error handling harder in the frontend and later in integration tests.

### Solution

I changed the endpoint to return a proper `404 Not Found` response using `HTTPException`.

```python
status = r.hget(f"job:{job_id}", "status")
if not status:
    raise HTTPException(status_code=404, detail="job not found")
```

## `api/main.py` after line 8

```python
app = FastAPI()

r = redis.Redis(host="localhost", port=6379)
```

### Problem

The API had no health endpoint. That would make Docker health checks, CI integration checks, and rolling deployment verification much harder because there would be no reliable way to tell whether the API was actually ready.

### Solution

I added a `/health` endpoint that checks Redis connectivity and returns `503` if Redis is unavailable.

```python
@app.get("/health")
def healthcheck():
    try:
        r.ping()
        return {"status": "ok"}
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="redis unavailable") from exc
```

## `worker/worker.py` line 6

```python
r = redis.Redis(host="localhost", port=6379)
```

### Problem

The worker also hardcoded Redis to `localhost:6379`. That would fail in Docker for the same reason as the API: `localhost` inside the worker container is not the Redis container.

### Solution

I changed the worker to use the same environment-based Redis configuration pattern.

```python
def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )
```

## `worker/worker.py` lines 14-18

```python
while True:
    job = r.brpop("job", timeout=5)
    if job:
        _, job_id = job
        process_job(job_id.decode())
```

### Problem

The worker loop ran immediately when the file was imported. That makes testing difficult, makes the module less reusable, and is a poor pattern for production processes that should have an explicit entrypoint.

### Solution

I moved the loop into a `main()` function and added the standard module guard.

```python
def main():
    while RUNNING:
        job = r.brpop("job", timeout=5)
        if not job:
            continue

        _, job_id = job
        process_job(job_id)


if __name__ == "__main__":
    main()
```

## `worker/worker.py` lines 14-18

```python
while True:
    job = r.brpop("job", timeout=5)
    if job:
        _, job_id = job
        process_job(job_id.decode())
```

### Problem

The worker did not handle shutdown signals. In containers, stop and restart operations typically send `SIGTERM`, and without handling that signal the process may exit abruptly instead of stopping cleanly.

### Solution

I added `SIGINT` and `SIGTERM` handlers and made the loop check a `RUNNING` flag.

```python
RUNNING = True


def handle_shutdown(signum, _):
    global RUNNING
    RUNNING = False
    print(f"Received signal {signum}, shutting down worker loop...")


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
```


## `worker/worker.py` lines 8-12

```python
def process_job(job_id):
    print(f"Processing job {job_id}")
    time.sleep(2)  # simulate work
    r.hset(f"job:{job_id}", "status", "completed")
    print(f"Done: {job_id}")
```

### Problem

If anything failed during job processing, the worker would leave the job without a terminal failure state. That would make failed jobs look stuck forever.

### Solution

I wrapped processing in `try/except` and update the job status to `failed` before logging the failed job.

```python
def process_job(job_id: str):
    print(f"Processing job {job_id}")
    try:
        time.sleep(2)
        r.hset(f"job:{job_id}", "status", "completed")
        print(f"Done: {job_id}")
    except Exception:
        r.hset(f"job:{job_id}", "status", "failed")
        print(f"Failed: {job_id}")
```

## `frontend/app.js` line 6

```javascript
const API_URL = "http://localhost:8000";
```

### Problem

The frontend was hardcoded to call the API at `http://localhost:8000`. That breaks in containers and makes deployment configuration inflexible because the frontend should get its backend URL from the environment.

### Solution

I changed the frontend to read `API_URL` from environment variables, with localhost only as a fallback for local development.

```javascript
const API_URL = process.env.API_URL || 'http://localhost:8000';
```

## `frontend/app.js` lines 29-31

```javascript
app.listen(3000, () => {
  console.log('Frontend running on port 3000');
});
```

### Problem

The frontend listened only on the default host. In containers, services should bind to `0.0.0.0` so they are reachable from outside the container.

### Solution

I added configurable `HOST` and `PORT` values and bound the app to `0.0.0.0` by default.

```javascript
const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Frontend running on http://${HOST}:${PORT}`);
});
```

## `frontend/app.js` lines 11-26

```javascript
app.post('/submit', async (req, res) => {
  try {
    const response = await axios.post(`${API_URL}/jobs`);
    res.json(response.data);
  } catch (err) {
    res.status(500).json({ error: "something went wrong" });
  }
});

app.get('/status/:id', async (req, res) => {
  try {
    const response = await axios.get(`${API_URL}/jobs/${req.params.id}`);
    res.json(response.data);
  } catch (err) {
    res.status(500).json({ error: "something went wrong" });
  }
});
```

### Problem

The frontend turned every upstream API failure into the same generic HTTP 500 response. That hides useful information like `404` from the API and makes debugging much harder.

### Solution

I preserved the upstream status code when available and return `502` only when the API cannot be reached at all.

```javascript
app.post('/submit', async (_req, res) => {
  try {
    const response = await axios.post(`${API_URL}/jobs`);
    res.json(response.data);
  } catch (err) {
    const status = err.response?.status || 502;
    const detail = err.response?.data || { error: 'API unavailable' };
    res.status(status).json(detail);
  }
});
```

## `frontend/app.js` after line 9

```javascript
app.use(express.json());
app.use(express.static(path.join(__dirname, 'views')));
```

### Problem

The frontend had no health endpoint, so there was no simple way for Docker or a deployment script to verify that the service itself was ready.

### Solution

I added a lightweight `/health` endpoint.

```javascript
app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});
```

## `frontend/views/index.html` lines 23-37

```javascript
async function submitJob() {
  const res = await fetch('/submit', { method: 'POST' });
  const data = await res.json();
  document.getElementById('result').innerText = `Submitted: ${data.job_id}`;
  jobIds.push(data.job_id);
  pollJob(data.job_id);
}

async function pollJob(id) {
  const res = await fetch(`/status/${id}`);
  const data = await res.json();
  renderJob(id, data.status);
  if (data.status !== 'completed') {
    setTimeout(() => pollJob(id), 2000);
  }
}
```

### Problem

The page assumed every request succeeded. If submission failed or the status endpoint returned an error, the UI could show undefined values or keep polling with invalid state.

### Solution

I added error handling around both submit and polling, and I stop polling when the job reaches a terminal `failed` state.

```javascript
async function submitJob() {
  try {
    const res = await fetch('/submit', { method: 'POST' });
    const data = await res.json();

    if (!res.ok || !data.job_id) {
      throw new Error(data.detail || data.error || 'Unable to submit job');
    }

    setResult(`Submitted: ${data.job_id}`);
    pollJob(data.job_id);
  } catch (error) {
    setResult(`Error: ${error.message}`);
  }
}
```


## `.gitignore` lines 1-3

```gitignore
.venv

__pycache__
node_modules
```

### Problem

The repository ignored virtual environments and dependencies, but it did not ignore `.env` files.

### Solution

I added `.env` patterns and kept `.env.example` explicitly allowed.

```gitignore
.venv
__pycache__/
.pytest_cache/
node_modules/
.env
.env.*
!.env.example
```
