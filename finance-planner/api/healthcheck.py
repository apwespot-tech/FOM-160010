import sys
import urllib.request

HEALTH_URL = "http://127.0.0.1:8000/api/health"
TIMEOUT_SECONDS = 3


def main() -> int:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=TIMEOUT_SECONDS) as response:
            status_code = response.status
    except OSError:
        return 1

    if status_code != 200:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
