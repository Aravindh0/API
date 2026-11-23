
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Security
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader

app = FastAPI(
    title="Fabric CSV Ingestion API",
    version="1.0.0",
    description="API to ingest CSV files from GitHub into Fabric Lakehouse"
)

# --------------------------------------------------
# API KEY AUTHENTICATION
# --------------------------------------------------

API_KEY = os.getenv("API_KEY")

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False
)

def verify_api_key(
    api_key: str = Security(api_key_header)
):
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="API key not configured"
        )

    if not api_key or not secrets.compare_digest(
        api_key, API_KEY
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return api_key


# --------------------------------------------------
# CSV ROOT DIRECTORY
# --------------------------------------------------

# If main.py is at the repository root and your CSVs
# are inside a folder named "Custom API", use this.
DATA_ROOT = (
    Path(__file__).resolve().parent / "Custom API"
).resolve()

# If CSV dataset folders are directly beside main.py,
# replace DATA_ROOT with:
# DATA_ROOT = Path(__file__).resolve().parent


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Fabric CSV API"
    }


# --------------------------------------------------
# LIST ALL CSV FILES
# --------------------------------------------------

@app.get("/api/v1/files")
def list_files(
    api_key: str = Security(verify_api_key)
):
    files = []

    for csv_file in sorted(DATA_ROOT.rglob("*.csv")):

        if not csv_file.is_file():
            continue

        resolved_file = csv_file.resolve()

        if not resolved_file.is_relative_to(DATA_ROOT):
            continue

        relative_path = csv_file.relative_to(DATA_ROOT)
        parts = relative_path.parts

        files.append({
            "dataset": parts[0],
            "dateFolder": parts[1] if len(parts) > 2 else "",
            "fileName": csv_file.name,
            "relativePath": relative_path.as_posix(),
            "destinationFolder": relative_path.parent.as_posix()
        })

    return {
        "totalFiles": len(files),
        "files": files
    }


# --------------------------------------------------
# DOWNLOAD ORIGINAL CSV FILE
# --------------------------------------------------

@app.get("/api/v1/download/{file_path:path}")
def download_csv(
    file_path: str,
    api_key: str = Security(verify_api_key)
):
    target = (DATA_ROOT / file_path).resolve()

    # Validate requested file path
    if not target.is_relative_to(DATA_ROOT):
        raise HTTPException(
            status_code=403,
            detail="Invalid file path"
        )

    if not target.is_file() or target.suffix.lower() != ".csv":
        raise HTTPException(
            status_code=404,
            detail="CSV file not found"
        )

    return FileResponse(
        path=target,
        media_type="text/csv",
        filename=target.name
    )
