"""
Simple script to run the HS Code Classifier application
"""
import uvicorn

if __name__ == "__main__":
    print("🌍 Starting HS Code Classifier...")
    print("📡 Server will be available at: http://localhost:7001")
    print("🛑 Press CTRL+C to stop the server\n")
    
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=7001,
        reload=True,
        log_level="info"
    )
