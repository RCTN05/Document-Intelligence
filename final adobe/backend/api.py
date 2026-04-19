from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import shutil
import os
import uuid
from main import run_pipeline

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "data/input_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==============================
# Upload
# ==============================
@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    filenames = []

    print("📥 Received files:", [f.filename for f in files])

    for file in files:
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        filenames.append(unique_name)

    print("✅ Saved files:", filenames)

    return {"files": filenames}

# ==============================
# Process
# ==============================
@app.post("/process")
async def process_docs(request: dict):
    if "files" not in request or "query" not in request:
        raise HTTPException(status_code=400, detail="Missing files or query")

    print("⚙️ Processing files:", request["files"])

    input_data = {
        "documents": [{"filename": f} for f in request["files"]],
        "persona": {"role": request.get("persona", "Analyst")},
        "job_to_be_done": {"task": request["query"]}
    }

    result = run_pipeline(input_data)

    return result