from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
import os

app = FastAPI(title="HS Code Classifier", version="1.0.0")

# Include API routes
app.include_router(router)

# Mount uploads directory if it exists
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
