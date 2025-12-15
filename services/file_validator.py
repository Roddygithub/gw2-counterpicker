"""
File validation service - Security checks for uploaded files
"""

from fastapi import UploadFile, HTTPException
from pathlib import Path
import zipfile
import io

# Security constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.evtc', '.zevtc', '.zip'}
ALLOWED_MIME_TYPES = {
    'application/octet-stream',
    'application/zip',
    'application/x-zip-compressed',
    'application/x-evtc'
}


async def validate_upload_file(file: UploadFile) -> bytes:
    """
    Validate uploaded file for security
    
    Args:
        file: Uploaded file
        
    Returns:
        File content as bytes
        
    Raises:
        HTTPException: If validation fails
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Validate ZIP files
    if file_ext == '.zip':
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Check for zip bombs (too many files or nested zips)
                if len(zf.namelist()) > 100:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP contains too many files (max 100)"
                    )
                
                # Check for dangerous files
                for name in zf.namelist():
                    if name.startswith('/') or '..' in name:
                        raise HTTPException(
                            status_code=400,
                            detail="ZIP contains invalid file paths"
                        )
                    
                    # Check file extension in ZIP
                    zip_ext = Path(name).suffix.lower()
                    if zip_ext not in {'.evtc', '.zevtc'}:
                        raise HTTPException(
                            status_code=400,
                            detail=f"ZIP must only contain .evtc or .zevtc files"
                        )
                
                # Check total uncompressed size
                total_size = sum(info.file_size for info in zf.infolist())
                if total_size > MAX_FILE_SIZE * 2:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP uncompressed size too large"
                    )
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid or corrupted ZIP file")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"ZIP validation error: {str(e)}")
    
    return content
