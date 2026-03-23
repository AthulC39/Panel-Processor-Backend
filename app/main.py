from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List
from pathlib import Path
import shutil
import uuid
import zipfile

from app.processor import run_processing_pipeline
from app.converter import convert_dwg_files_to_dxf

BASE_DIR = Path(__file__).resolve().parent.parent
FILES_DIR = BASE_DIR / "files"
UPLOADS_DIR = FILES_DIR / "uploads"
OUTPUT_DIR = FILES_DIR / "output"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="CAD Processing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


def _safe_extract_zip(zip_path: Path, extract_to: Path) -> None:
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            member_path = extract_to / member.filename
            resolved = member_path.resolve()
            if not str(resolved).startswith(str(extract_to.resolve())):
                raise ValueError("ZIP contains invalid paths.")
        zip_ref.extractall(extract_to)


def _collect_cad_files(root: Path) -> tuple[list[Path], list[Path]]:
    root = Path(root)

    dwg_files = []
    dxf_files = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        if suffix == ".dwg":
            dwg_files.append(path)
        elif suffix == ".dxf":
            dxf_files.append(path)

    return dwg_files, dxf_files


def _copy_dxf_files_to_processing_dir(dxf_files: list[Path], processing_dir: Path) -> list[Path]:
    processing_dir = Path(processing_dir)
    processing_dir.mkdir(parents=True, exist_ok=True)

    copied = []

    for index, src in enumerate(dxf_files, start=1):
        dest = processing_dir / f"{index:05d}_{src.stem}.dxf"
        shutil.copy2(src, dest)
        copied.append(dest)

    return copied


@app.post("/process")
async def process_cad(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    job_id = str(uuid.uuid4())
    job_upload_dir = UPLOADS_DIR / job_id
    job_output_dir = OUTPUT_DIR / job_id
    extracted_zip_dir = job_upload_dir / "zip_extracted"
    processing_dir = job_output_dir / "processing_dxf"
    converted_dxf_dir = job_output_dir / "converted_dxf"

    job_upload_dir.mkdir(parents=True, exist_ok=True)
    job_output_dir.mkdir(parents=True, exist_ok=True)
    extracted_zip_dir.mkdir(parents=True, exist_ok=True)
    processing_dir.mkdir(parents=True, exist_ok=True)
    converted_dxf_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []

    try:
        zip_uploads = 0

        for file in files:
            filename = file.filename or "uploaded_file"
            ext = Path(filename).suffix.lower()

            if ext not in [".dwg", ".dxf", ".zip"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {filename}",
                )

            if ext == ".zip":
                zip_uploads += 1

            destination = job_upload_dir / filename
            with destination.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            saved_paths.append(destination)

        if zip_uploads > 1:
            raise HTTPException(status_code=400, detail="Only one ZIP upload is allowed per request.")

        if zip_uploads == 1 and len(saved_paths) > 1:
            raise HTTPException(
                status_code=400,
                detail="Upload either one ZIP file or a set of DWG/DXF files, not both together.",
            )

        dwg_files: list[Path] = []
        dxf_files: list[Path] = []

        if zip_uploads == 1:
            zip_file = next(p for p in saved_paths if p.suffix.lower() == ".zip")
            _safe_extract_zip(zip_file, extracted_zip_dir)
            dwg_files, dxf_files = _collect_cad_files(extracted_zip_dir)
        else:
            dwg_files = [p for p in saved_paths if p.suffix.lower() == ".dwg"]
            dxf_files = [p for p in saved_paths if p.suffix.lower() == ".dxf"]

        if not dwg_files and not dxf_files:
            raise HTTPException(
                status_code=400,
                detail="No DWG or DXF files were found in the upload.",
            )

        copied_dxf_files = _copy_dxf_files_to_processing_dir(dxf_files, processing_dir)
        converted_dxf_files = convert_dwg_files_to_dxf(dwg_files, processing_dir) if dwg_files else []

        all_dxf_inputs = copied_dxf_files + converted_dxf_files

        if not all_dxf_inputs:
            raise HTTPException(
                status_code=500,
                detail="No DXF files were available for processing after upload/conversion.",
            )

        result = run_processing_pipeline(
            input_files=all_dxf_inputs,
            output_dir=job_output_dir,
        )

        output_file = Path(result["output_file"])
        record_count = result.get("record_count", 0)

        if not output_file.exists():
            raise HTTPException(status_code=500, detail="Output file was not created.")

        return FileResponse(
            path=str(output_file),
            filename=output_file.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "X-Job-Id": job_id,
                "X-Record-Count": str(record_count),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")