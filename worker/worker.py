import redis
import time
import os
import signal


RUNNING = True


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )


r = get_redis_client()


def handle_shutdown(signum, _):
    global RUNNING
    RUNNING = False
    print(f"Received signal {signum}, shutting down worker loop...")


def process_job(job_id: str):
    print(f"Processing job {job_id}")
    try:
        time.sleep(2)  # simulate work
        r.hset(f"job:{job_id}", "status", "completed")
        print(f"Done: {job_id}")
    except Exception:
        r.hset(f"job:{job_id}", "status", "failed")
        print(f"Failed: {job_id}")


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    while RUNNING:
        job = r.brpop("job", timeout=5)
        if not job:
            continue

        _, job_id = job  # type: ignore
        process_job(job_id)


if __name__ == "__main__":
    main()
