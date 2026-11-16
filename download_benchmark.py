#!/usr/bin/env python3
"""Make ten sequential HTTP requests and report download metrics."""

import argparse
import time
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


REQUEST_COUNT = 10
TIMEOUT_SECONDS = 30
CHUNK_SIZE = 64 * 1024


def valid_url(value):
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("URL must start with http:// or https://")
    return value


def download_once(url, number):
    started = time.perf_counter()
    downloaded = 0
    status = None
    error = None
    complete = False

    try:
        request = Request(url, headers={"User-Agent": "10requesttest/1.0"})
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    complete = True
                    break
                downloaded += len(chunk)
    except HTTPError as exc:
        status = exc.code
        try:
            while True:
                chunk = exc.read(CHUNK_SIZE)
                if not chunk:
                    complete = True
                    break
                downloaded += len(chunk)
        except IncompleteRead as read_error:
            downloaded += len(read_error.partial)
            error = f"{type(read_error).__name__}: {read_error}"
        except Exception as read_error:
            error = f"{type(read_error).__name__}: {read_error}"
        finally:
            exc.close()
    except IncompleteRead as exc:
        downloaded += len(exc.partial)
        error = f"{type(exc).__name__}: {exc}"
    except (URLError, TimeoutError, OSError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    elapsed = time.perf_counter() - started
    success = status is not None and 200 <= status < 300 and complete and error is None
    if status is not None and not (200 <= status < 300):
        error = f"HTTP status {status}"

    label = "успех" if success else "неуспех"
    details = f"HTTP {status}" if status is not None else (error or "ошибка запроса")
    if error and status is not None and 200 <= status < 300:
        details += f", {error}"
    print(f"Запрос {number:02d}: {label} — {details}; {elapsed:.3f} с; {downloaded} байт")

    return {
        "success": success,
        "elapsed": elapsed,
        "downloaded": downloaded,
    }


def main():
    parser = argparse.ArgumentParser(
        description=f"Выполняет {REQUEST_COUNT} последовательных HTTP-запросов и измеряет загрузку."
    )
    parser.add_argument("url", type=valid_url, help="URL ресурса (HTTP или HTTPS)")
    args = parser.parse_args()

    results = [download_once(args.url, number) for number in range(1, REQUEST_COUNT + 1)]
    successful = [result for result in results if result["success"]]
    failed_count = REQUEST_COUNT - len(successful)
    total_downloaded = sum(result["downloaded"] for result in results)

    print("\nИтог:")
    print(f"Успешных запросов: {len(successful)}")
    print(f"Неуспешных запросов: {failed_count}")
    print(f"Всего скачано: {total_downloaded} байт ({total_downloaded / 1_000_000:.3f} MB)")

    if successful:
        average_time = sum(result["elapsed"] for result in successful) / len(successful)
        successful_bytes = sum(result["downloaded"] for result in successful)
        successful_time = sum(result["elapsed"] for result in successful)
        speed = successful_bytes / successful_time if successful_time else 0.0
        print(f"Среднее время успешного запроса: {average_time:.3f} с")
        print(f"Скорость успешных загрузок: {speed / 1_000_000:.3f} MB/s")
    else:
        print("Среднее время успешного запроса: нет успешных запросов")
        print("Скорость успешных загрузок: нет успешных запросов")


if __name__ == "__main__":
    main()
