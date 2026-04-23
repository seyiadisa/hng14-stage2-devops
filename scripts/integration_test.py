import json
import os
import time
import urllib.error
import urllib.request


FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:3000")
TIMEOUT_SECONDS = int(os.getenv("INTEGRATION_TIMEOUT_SECONDS", "60"))
POLL_INTERVAL_SECONDS = int(os.getenv("INTEGRATION_POLL_INTERVAL_SECONDS", "2"))


def request_json(method: str, url: str) -> dict:
    request = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    submit_response = request_json("POST", f"{FRONTEND_URL}/submit")
    job_id = submit_response["job_id"]
    print(f"Submitted job {job_id}")

    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        status_response = request_json("GET", f"{FRONTEND_URL}/status/{job_id}")
        status = status_response["status"]
        print(f"Job {job_id} status: {status}")

        if status == "completed":
            return

        if status == "failed":
            raise RuntimeError(f"Job {job_id} failed")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Job {job_id} did not complete within {TIMEOUT_SECONDS} seconds")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as exc:
        raise SystemExit(f"Integration request failed: {exc}") from exc
