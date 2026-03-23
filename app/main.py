from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List
from pathlib import Path
import shutil
import uuid

from app.processor import run_processing_pipeline
from app.converter import convert_dwg_to_dxf_in_place

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
     
        "https://infin8cadbomgenerator.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/process")
async def process_cad(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    job_id = str(uuid.uuid4())
    job_upload_dir = UPLOADS_DIR / job_id
    job_output_dir = OUTPUT_DIR / job_id
    job_dxf_dir = job_output_dir / "dxf"

    job_upload_dir.mkdir(parents=True, exist_ok=True)
    job_output_dir.mkdir(parents=True, exist_ok=True)
    job_dxf_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []

    try:
        for file in files:
            filename = file.filename or "uploaded_file"
            ext = Path(filename).suffix.lower()

            if ext not in [".dwg", ".dxf"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {filename}",
                )

            destination = job_upload_dir / filename
            with destination.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            saved_paths.append(destination)

        dwg_files = [p for p in saved_paths if p.suffix.lower() == ".dwg"]
        dxf_files = [p for p in saved_paths if p.suffix.lower() == ".dxf"]

        converted_dxf_files = []
        if dwg_files:
            converted_dxf_files = convert_dwg_to_dxf_in_place(
                input_dir=job_upload_dir,
                output_dir=job_dxf_dir,
            )

        all_dxf_inputs = dxf_files + converted_dxf_files

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