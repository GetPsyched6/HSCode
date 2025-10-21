# HS Code Classifier

AI-powered HS (Harmonized System) code classification using IBM WatsonX and Llama 3.2 90B Vision model.

## Overview

This application uses computer vision and AI to automatically classify products into their appropriate HS codes based on uploaded images. The system analyzes product images and matches them against a knowledge base of HS codes to provide:

- **Primary HS Code Classification**: The most likely HS code for the product
- **Confidence Scoring**: How confident the AI is in its classification (0-100%)
- **Detailed Reasoning**: Explanation of why the specific code was chosen
- **Alternative Codes**: Other potential HS codes that might apply
- **Key Characteristics**: Identified product attributes that influenced the classification

## Features

- 🎯 **Multiple Classification Options**: AI returns 1-3 possible HS codes ranked by confidence
- 📊 **Visual Analysis**: Detailed inspection of color, processing state, and product characteristics
- 🔍 **Evidence-Based Reasoning**: Each classification includes detailed reasoning citing visual evidence
- 💯 **Confidence Scoring**: Rigorous confidence metrics (0-100%) for each classification
- 🃏 **Card-Based UI**: Multiple classification options displayed as easy-to-compare cards
- 🎨 **Modern UI**: Clean, responsive interface with dark/light theme support
- ⚡ **Fast Processing**: Results typically returned in 20-30 seconds
- 📱 **Drag & Drop**: Easy image upload with drag-and-drop support
- 🛡️ **Robust JSON Parsing**: Advanced fallback parsing handles markdown and malformed responses

## Technology Stack

- **Backend**: FastAPI (Python)
- **AI Model**: IBM WatsonX - Llama 3.2 90B Vision Instruct
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Image Processing**: PIL (Pillow)

## Prerequisites

- Python 3.8 or higher
- IBM Cloud account with WatsonX access
- WatsonX API Key and Project ID

## Installation

1. **Clone or download the project**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   The `.env` file already exists in the root directory with your credentials:
   ```
   WATSONX_API_KEY=your_api_key
   WATSONX_PROJECT_ID=your_project_id
   WATSONX_URL=https://us-south.ml.cloud.ibm.com
   ```

4. **Create uploads directory**
   ```bash
   mkdir uploads
   ```

## Running the Application

Start the server using Uvicorn:

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

Then open your browser to:
```
http://localhost:8000
```

## Usage

1. **Upload an Image**: Click the upload area or drag and drop a product image
2. **Classify**: Click the "Classify HS Code" button
3. **View Results**: The AI will analyze the image and display:
   - **Visual Analysis Summary**: Product type, color, processing state
   - **Multiple Classification Cards**: 1-3 possible HS codes ordered by confidence
   - **Top Match Highlighted**: Primary classification clearly marked with ⭐
   - **Per-Card Details**:
     - HS code and statistical suffix
     - Confidence score with visual bar (0-100%)
     - Official HS code description
     - Product description from the image
     - Detailed reasoning citing visual evidence
     - Key characteristics identified

## Project Structure

```
HS_Code/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application
│   │   └── routes.py        # API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Configuration and HS code document
│   └── services/
│       ├── __init__.py
│       └── watsonx_service.py  # WatsonX API integration
├── frontend/
│   └── templates/
│       └── index.html       # Web UI
├── uploads/                 # Temporary image storage
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## HS Code Document

The current implementation includes a sample HS code document covering:
- **0901**: Coffee and coffee products
- **0902**: Tea (green, black, fermented)
- **0903**: Maté

The HS code document can be expanded in `app/core/config.py` by modifying the `HS_CODE_DOCUMENT` variable.

## API Endpoints

- `GET /` - Serves the web UI
- `POST /api/classify-hs-code` - Classifies uploaded image
  - Request: multipart/form-data with `file` field
  - Response: JSON with classification results

## Limitations

- Currently only supports HS codes included in the configured document
- Image analysis quality depends on image clarity and product visibility
- Processing time: ~20-30 seconds per image
- Maximum image size: 10MB
- Supported formats: JPG, PNG, GIF, WebP

## Extending the HS Code Database

To add more HS codes:

1. Open `app/core/config.py`
2. Update the `HS_CODE_DOCUMENT` variable with additional HS code entries
3. Follow the same CSV format: Heading/Subheading, Stat. Suffix, Article Description, Unit, Rates...

## Troubleshooting

**Issue**: "Failed to get access token"
- Solution: Verify your WatsonX API key in `.env` file

**Issue**: "API call failed: 401"
- Solution: Check that your WatsonX project ID is correct

**Issue**: Images not uploading
- Solution: Ensure the `uploads/` directory exists and has write permissions

**Issue**: Slow classification
- Solution: This is normal - the vision model takes 20-30 seconds to analyze images

## Development

Based on the `overgoods` project structure, this application follows similar patterns:

- FastAPI for the backend API
- WatsonX integration for AI inference
- Modern, responsive UI with theme support
- Modular architecture for easy extension

## License

This project is for educational and demonstration purposes.

## Credits

Built using IBM WatsonX and Meta's Llama 3.2 90B Vision Instruct model.
