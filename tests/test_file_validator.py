"""
Tests for file validation service
"""

import pytest
import io
import zipfile
from fastapi import HTTPException, UploadFile

from services.file_validator import validate_upload_file, MAX_FILE_SIZE


class MockUploadFile:
    """Mock UploadFile for testing"""
    def __init__(self, filename, content):
        self.filename = filename
        self.content = content
    
    async def read(self):
        return self.content


@pytest.mark.asyncio
async def test_validate_valid_evtc_file():
    """Test validation of valid EVTC file"""
    file = MockUploadFile("test.evtc", b"EVTC" + b"\x00" * 100)
    content = await validate_upload_file(file)
    assert content == b"EVTC" + b"\x00" * 100


@pytest.mark.asyncio
async def test_validate_valid_zevtc_file():
    """Test validation of valid ZEVTC file"""
    file = MockUploadFile("test.zevtc", b"ZEVTC" + b"\x00" * 100)
    content = await validate_upload_file(file)
    assert content == b"ZEVTC" + b"\x00" * 100


@pytest.mark.asyncio
async def test_reject_invalid_extension():
    """Test rejection of invalid file extension"""
    file = MockUploadFile("test.txt", b"invalid")
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload_file(file)
    assert exc_info.value.status_code == 400
    assert "Invalid file type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_reject_no_filename():
    """Test rejection of file without filename"""
    file = MockUploadFile(None, b"content")
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload_file(file)
    assert exc_info.value.status_code == 400
    assert "No filename provided" in exc_info.value.detail


@pytest.mark.asyncio
async def test_reject_empty_file():
    """Test rejection of empty file"""
    file = MockUploadFile("test.evtc", b"")
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload_file(file)
    assert exc_info.value.status_code == 400
    assert "Empty file" in exc_info.value.detail


@pytest.mark.asyncio
async def test_reject_file_too_large():
    """Test rejection of file exceeding size limit"""
    large_content = b"X" * (MAX_FILE_SIZE + 1)
    file = MockUploadFile("test.evtc", large_content)
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload_file(file)
    assert exc_info.value.status_code == 413
    assert "File too large" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_valid_zip():
    """Test validation of valid ZIP file"""
    # Create a valid ZIP with EVTC files
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("test1.evtc", b"EVTC" + b"\x00" * 100)
        zf.writestr("test2.zevtc", b"ZEVTC" + b"\x00" * 100)
    
    file = MockUploadFile("test.zip", zip_buffer.getvalue())
    content = await validate_upload_file(file)
    assert len(content) > 0


@pytest.mark.asyncio
async def test_reject_zip_with_too_many_files():
    """Test rejection of ZIP with too many files"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        for i in range(101):  # More than max allowed
            zf.writestr(f"test{i}.evtc", b"EVTC")
    
    file = MockUploadFile("test.zip", zip_buffer.getvalue())
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload_file(file)
    assert exc_info.value.status_code == 400
    assert "too many files" in exc_info.value.detail


@pytest.mark.asyncio
async def test_reject_zip_with_invalid_files():
    """Test rejection of ZIP containing non-EVTC files"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("test.txt", b"invalid")
    
    file = MockUploadFile("test.zip", zip_buffer.getvalue())
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload_file(file)
    assert exc_info.value.status_code == 400
    assert "must only contain .evtc or .zevtc" in exc_info.value.detail


@pytest.mark.asyncio
async def test_reject_zip_with_path_traversal():
    """Test rejection of ZIP with path traversal attempt"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("../evil.evtc", b"EVTC")
    
    file = MockUploadFile("test.zip", zip_buffer.getvalue())
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload_file(file)
    assert exc_info.value.status_code == 400
    assert "invalid file paths" in exc_info.value.detail
