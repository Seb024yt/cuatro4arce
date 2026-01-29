from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import uuid

from playwright.sync_api import Browser, Page

@dataclass
class DownloadResult:
    run_id: str
    saved_path: Path

def make_run_dir(base_dir: Path, company_id: str) -> Path:
    run_id = str(uuid.uuid4())
    run_dir = base_dir / "companies" / company_id / "runs" / run_id
    (run_dir / "downloads").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    return run_dir

def download_file(page: Page, target_url: str, click_selector: str, run_dir: Path) -> DownloadResult:
    """
    Navega a target_url y dispara una descarga haciendo click en click_selector.
    Guarda el archivo en run_dir/downloads/<suggested_filename>
    """
    page.goto(target_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    download_dir = run_dir / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    with page.expect_download() as dl_info:
        page.locator(click_selector).first.click()

    download = dl_info.value
    suggested = download.suggested_filename
    save_path = download_dir / suggested
    download.save_as(str(save_path))

    return DownloadResult(run_id=run_dir.name, saved_path=save_path)
