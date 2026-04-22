from fastapi import FastAPI, HTTPException
import redis
import uuid
import os


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )


app = FastAPI()

r = get_redis_client()


@app.get("/health")
def healthcheck():
    try:
        r.ping()
        return {"status": "ok"}
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="redis unavailable") from exc


@app.post("/jobs")
def create_job():
    job_id = str(uuid.uuid4())
    r.hset(f"job:{job_id}", mapping={"status": "queued"})
    r.lpush("job", job_id)
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    status = r.hget(f"job:{job_id}", "status")
    if not status:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job_id, "status": status}
