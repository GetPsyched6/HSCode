from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import os
import uuid
import shutil
import hashlib
import random
from pathlib import Path

from app.services.watsonx_service import WatsonxHSCodeClassifier
from app.core.config import UPLOAD_DIR, ALLOWED_EXTENSIONS

router = APIRouter()

# Initialize classifier
classifier = WatsonxHSCodeClassifier()


def generate_customs_clearance_data(hs_code: str) -> dict:
    """
    Generate realistic customs clearance trend data based on HS code.
    Uses HS code as seed for consistent but varied data.
    """
    # Use HS code as seed for consistent data
    seed = int(hashlib.md5(hs_code.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    
    # Base percentages that sum to 100%
    base_percentages = [6.4, 24.3, 25.1, 17.2, 9.6, 5.9, 11.5]
    
    # Add some variation based on HS code characteristics
    variation_factor = (seed % 100) / 100.0  # 0.0 to 0.99
    
    # Adjust percentages with some realistic variation
    adjusted_percentages = []
    for i, base in enumerate(base_percentages):
        # Add variation: ±15% of base value
        variation = (random.random() - 0.5) * 0.3 * base
        adjusted = max(0.1, base + variation)  # Ensure minimum 0.1%
        adjusted_percentages.append(adjusted)
    
    # Normalize to ensure they sum to 100%
    total = sum(adjusted_percentages)
    normalized_percentages = [round((p / total) * 100, 1) for p in adjusted_percentages]
    
    # Ensure they still sum to 100% (adjust last item if needed)
    current_total = sum(normalized_percentages)
    if current_total != 100.0:
        normalized_percentages[-1] = round(100.0 - sum(normalized_percentages[:-1]), 1)
    
    # Create the data structure
    clearance_data = {
        "summary": f"{sum(normalized_percentages[:4]):.1f}% of customs clearance takes ≤ 4 days",
        "data": [
            {"days": "1 day", "percentage": normalized_percentages[0]},
            {"days": "2 days", "percentage": normalized_percentages[1]},
            {"days": "3 days", "percentage": normalized_percentages[2]},
            {"days": "4 days", "percentage": normalized_percentages[3]},
            {"days": "5 days", "percentage": normalized_percentages[4]},
            {"days": "6 days", "percentage": normalized_percentages[5]},
            {"days": "> 6 days", "percentage": normalized_percentages[6]}
        ]
    }
    
    return clearance_data


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
            # Generate customs clearance data for the primary HS code
            data = result["data"]
            customs_data = None
            
            # Get the primary HS code (first classification or single result)
            if isinstance(data, dict):
                if "classifications" in data and len(data["classifications"]) > 0:
                    primary_hs_code = data["classifications"][0]["hs_code"]
                elif "hs_code" in data:
                    primary_hs_code = data["hs_code"]
                else:
                    primary_hs_code = None
                
                if primary_hs_code:
                    customs_data = generate_customs_clearance_data(primary_hs_code)
            
            return JSONResponse(
                content={
                    "success": True,
                    "data": data,
                    "customs_clearance": customs_data,
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
