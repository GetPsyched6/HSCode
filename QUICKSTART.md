# Quick Start Guide

Get up and running with the HS Code Classifier in 3 simple steps!

## Step 1: Install Dependencies

Open a terminal in the project directory and run:

```bash
pip install -r requirements.txt
```

This will install:
- FastAPI (web framework)
- Uvicorn (web server)
- Python-multipart (file upload support)
- Python-dotenv (environment variable management)
- Requests (HTTP client for WatsonX API)
- Pillow (image processing)

## Step 2: Start the Server

Run the application using the provided script:

```bash
python run.py
```

Or manually with uvicorn:

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
🌍 Starting HS Code Classifier...
📡 Server will be available at: http://localhost:8000
```

## Step 3: Open the Web Interface

Open your web browser and navigate to:

```
http://localhost:8000
```

## Using the Application

1. **Upload Image**: Click the upload area or drag & drop a product image
   - Supported formats: JPG, PNG, GIF, WebP
   - Max size: 10MB

2. **Classify**: Click "Classify HS Code" button

3. **Wait**: The AI will analyze the image (20-30 seconds)

4. **View Results**:
   - **HS Code**: The classified code (e.g., 0901.21.00)
   - **Confidence Score**: How certain the AI is (0-100%)
   - **Product Description**: What the AI sees in the image
   - **Reasoning**: Why this code was chosen
   - **Key Characteristics**: Identified product attributes
   - **Alternative Codes**: Other potential matches

## Example Test Images

Try uploading images of:
- ☕ Coffee products (roasted, decaffeinated, organic)
- 🍵 Tea products (green tea, black tea, in tea bags)
- 🧉 Maté products

The current HS code database covers:
- **0901.x**: Coffee and coffee substitutes
- **0902.x**: Tea (green, black, fermented)
- **0903.x**: Maté

## Toggle Dark/Light Mode

Click the sun/moon icon in the top-right corner to switch themes.

## Stopping the Server

Press `CTRL+C` in the terminal to stop the server.

## Troubleshooting

**Port already in use?**
```bash
# Use a different port
uvicorn app.api.main:app --reload --port 8080
```

**Module not found?**
```bash
# Make sure you're in the project directory
cd c:/Users/roshin/Downloads/HS_Code
# Reinstall dependencies
pip install -r requirements.txt
```

**API errors?**
- The `.env` file already contains your WatsonX credentials
- Check your internet connection
- Verify your WatsonX API key is active

## What's Next?

- Add more HS codes to `app/core/config.py`
- Test with different product images
- Review the confidence scores and reasoning
- Explore alternative code suggestions

Enjoy classifying! 🎯
