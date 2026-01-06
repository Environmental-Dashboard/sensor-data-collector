"""
Test Upload Endpoint
====================
A test endpoint for CSV uploads with API key authentication.

PURPOSE:
    This endpoint mimics the real external upload endpoint for testing.
    It allows you to verify that:
    - CSV data is formatted correctly
    - Authentication headers are sent properly
    - File upload is working
    
REAL ENDPOINT:
    https://oberlin.communityhub.cloud/api/data-hub/upload/csv
    
THIS ENDPOINT:
    http://localhost:8000/api/test/upload/csv

IMPORTANT:
    DO NOT COMMIT THIS FILE TO GITHUB!
    Add to .gitignore: backend/app/routers/test_upload.py
    
    The test API key is hardcoded for local testing only.

Author: Sensor Data Collector Team
"""

from fastapi import APIRouter, HTTPException, Header, UploadFile, File
from datetime import datetime, timezone
from typing import Optional
import csv
import io


router = APIRouter(prefix="/api/test", tags=["test"])


# =============================================================================
# TEST API KEY
# =============================================================================

# This is the test API key. Change it for your testing.
# In production, the real endpoint uses user tokens from oberlin.communityhub.cloud
TEST_API_KEY = "test-sensor-api-key-12345"


def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify the API key from Authorization header.
    
    Expected format: "Bearer <api_key>"
    
    Args:
        authorization: Value of Authorization header
        
    Returns:
        The verified token
        
    Raises:
        HTTPException: If auth fails
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Expected: Bearer <token>"
        )
    
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format. Expected: Bearer <token>"
        )
    
    token = parts[1]
    
    if token != TEST_API_KEY:
        raise HTTPException(
            status_code=403,
            detail=f"Invalid API key. Expected: {TEST_API_KEY}"
        )
    
    return token


# =============================================================================
# TEST UPLOAD ENDPOINT
# =============================================================================

@router.post(
    "/upload/csv",
    summary="Test CSV Upload",
    description="""
    Test endpoint for CSV file uploads.
    
    Mimics the real upload endpoint for local testing.
    
    **Authentication:**
    Include the header: `Authorization: Bearer test-sensor-api-key-12345`
    
    **Body:**
    Multipart file upload with a CSV file
    
    **Returns:**
    - Parsed CSV summary
    - Rows received
    - Column names
    - Sample data
    """
)
async def upload_csv(
    file: UploadFile = File(..., description="CSV file to upload"),
    authorization: Optional[str] = Header(None)
):
    """
    Test endpoint for CSV upload.
    
    Validates the upload and returns a summary of the received data.
    In production, this data would be stored in a database.
    """
    # Verify authentication
    verify_api_key(authorization)
    
    # Validate file type
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV file (.csv extension required)"
        )
    
    # Read file content
    content = await file.read()
    
    try:
        content_str = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be UTF-8 encoded"
        )
    
    # Parse CSV
    try:
        csv_reader = csv.DictReader(io.StringIO(content_str))
        rows = list(csv_reader)
    except csv.Error as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV format: {str(e)}"
        )
    
    # Build response
    return {
        "status": "success",
        "message": "CSV file uploaded and parsed successfully",
        "filename": file.filename,
        "file_size_bytes": len(content),
        "rows_received": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
        "sample_data": rows[0] if rows else None,
        "received_at": datetime.now(timezone.utc).isoformat()
    }


@router.get(
    "/health",
    summary="Test Endpoint Health",
    description="Check if the test endpoint is working and get the test API key."
)
async def test_health():
    """Health check for the test endpoint."""
    return {
        "status": "healthy",
        "endpoint": "/api/test/upload/csv",
        "method": "POST",
        "authentication": "Bearer token required",
        "test_api_key": TEST_API_KEY,
        "usage": f'curl -X POST http://localhost:8000/api/test/upload/csv -H "Authorization: Bearer {TEST_API_KEY}" -F "file=@data.csv"'
    }


@router.get(
    "/echo",
    summary="Echo Test",
    description="Simple echo endpoint to verify the server is running."
)
async def echo(message: str = "Hello"):
    """Echo back a message."""
    return {
        "echo": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
