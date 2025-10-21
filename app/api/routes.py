from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import os
import uuid
import shutil
from pathlib import Path

from app.services.watsonx_service import WatsonxHSCodeClassifier
from app.core.config import UPLOAD_DIR, ALLOWED_EXTENSIONS

router = APIRouter()

# Initialize classifier
classifier = WatsonxHSCodeClassifier()


def save_uploaded_file(upload_file: UploadFile) -> str:
    """Save uploaded file and return the file path"""
    # Validate file extension
    file_ext = Path(upload_file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {file_ext} not allowed")

    # Create upload directory if it doesn't exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        return file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")


@router.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main page"""
    with open("frontend/templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


@router.post("/api/classify-hs-code")
async def classify_hs_code(file: UploadFile = File(...)):
    """Classify product image to HS code"""
    try:
        # Save uploaded file
        file_path = save_uploaded_file(file)

        # Classify the image
        result = classifier.classify_hs_code(file_path)

        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass

        if result["success"]:
            return JSONResponse(
                content={
                    "success": True,
                    "data": result["data"],
                    "raw_response": result.get("raw_response", ""),
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": result["error"],
                    "raw_response": result.get("raw_response", ""),
                },
            )

    except Exception as e:
        return JSONResponse(
            status_code=500, content={"success": False, "error": str(e)}
        )
