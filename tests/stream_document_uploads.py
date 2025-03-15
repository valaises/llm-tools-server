import requests
import os
from pathlib import Path
import time


def stream_upload_document(file_path):
    upload_url = "https://llmtools.home.valerii.cc/v1/files/upload"

    file_name = file_path.name
    file_size = os.path.getsize(file_path)

    key = os.environ.get('LLM_PROXY_API_KEY')
    headers = {
        'Content-Type': 'application/octet-stream',
        'X-File-Name': file_name,
        'X-File-Role': 'document',
        'Authorization': f"Bearer {key}"
    }

    def file_generator():
        bytes_sent = 0
        start_time = time.time()

        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break

                bytes_sent += len(chunk)
                elapsed = time.time() - start_time
                if elapsed > 0:  # Avoid division by zero
                    speed = bytes_sent / elapsed / 1024 / 1024  # MB/s
                    percent = (bytes_sent / file_size) * 100
                    print(f"\rUploading: {percent:.1f}% ({bytes_sent}/{file_size} bytes) at {speed:.2f} MB/s", end="")

                yield chunk

    try:
        # Make the streaming request
        print(f"Starting upload of {file_name} ({file_size} bytes)")
        response = requests.post(
            upload_url,
            headers=headers,
            data=file_generator(),
            stream=True
        )
        print(response.content)
        print("\nUpload completed")

        response.raise_for_status()

        # Return the response as JSON
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"\nError uploading file: {e}")
        return {"status": "error", "message": str(e)}


file_path = Path(__file__).parent / "assets" / "resume-valerii.pdf"
chunk_size = 1024


if __name__ == "__main__":
    if not file_path.is_file():
        print(f"Error: File not found: {file_path}")
        quit(1)

    result = stream_upload_document(
        file_path,
    )

    print(f"Server response: {result}")
