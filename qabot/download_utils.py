import os
import httpx
from datetime import datetime, timedelta
import appdirs


def get_cache_dir(app_name: str) -> str:
    return appdirs.user_cache_dir(app_name)


def download_and_cache(url: str, cache_duration: timedelta = timedelta(days=30)):
    filename = url.split('/')[-1]
    cache_dir = get_cache_dir("qabot")
    file_path = os.path.join(cache_dir, filename)

    # Check if file exists and is within the cache duration
    if os.path.exists(file_path):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        if datetime.now() - file_mod_time < cache_duration:
            return file_path

    # Download and save the file
    response = httpx.get(url)
    if response.status_code == 200:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as file:
            file.write(response.content)
    else:
        raise Exception("Failed to download the file.") from response.raise_for_status()

    return file_path


if __name__ == '__main__':
    doc_url = "https://duckdb.org/duckdb-docs.pdf"
    download_and_cache(doc_url)
