import asyncio
import json
import threading

from pathlib import Path
from typing import Tuple

from core.globals import UPLOADS_DIR
from core.logger import warn, info
from core.repositories.files_repository import FilesRepository
from doc_search.extactor.coxit.file_reader import FileReader


def worker(
        stop_event: threading.Event,
        stats_repository: FilesRepository
):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        while not stop_event.is_set():
            process_files = stats_repository.get_files_by_filter_sync("processing_status = ?", ("",))
            if not process_files:
                stop_event.wait(30)
                continue

            for file in process_files:
                info(f"Extracting file: {file.file_name_orig}")
                file_path: Path = UPLOADS_DIR.joinpath(file.file_name)

                if not file_path.is_file():
                    file.processing_status = f"Error: file is missing on disk"
                    stats_repository.update_file_sync(file.file_name, file)
                    continue

                if file.file_role == "coxit_document":
                    with file_path.open("rb") as f:
                        file_content = f.read()

                    file_reader = FileReader(file_content, file.file_name_orig)
                    extracted_sections = file_reader.extract_text()

                    if not extracted_sections:
                        file.processing_status = "Error: no text extracted"
                        stats_repository.update_file_sync(file.file_name, file)
                        continue

                    jsonl_file = file_path.with_suffix('.jsonl')

                    with jsonl_file.open("w") as f:
                        for section in extracted_sections:
                            f.write(json.dumps(section.to_dict()) + "\n")

                    file.processing_status = "extracted"
                    stats_repository.update_file_sync(file.file_name, file)
                    info(f"Extracting file {file.file_name_orig} OK")

                else:
                    warn(f"Unknown file_role: {file.file_role}: SKIPPING for now")

            stop_event.wait(5)

    finally:
        loop.close()


def spawn_worker(
        files_repository: FilesRepository,
) -> Tuple[threading.Event, threading.Thread]:
    """
    Spawn a worker thread

    Returns:
        Tuple of (stop_event, thread)
    """
    stop_event = threading.Event()
    worker_thread = threading.Thread(
        target=worker,
        args=(stop_event, files_repository),
        daemon=True
    )
    worker_thread.start()

    return stop_event, worker_thread
