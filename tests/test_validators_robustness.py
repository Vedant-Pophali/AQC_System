import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.validators.audio.validate_loudness import check_loudness as validate
except ImportError as e:
    print(f"\nCRITICAL IMPORT ERROR: {e}")
    # Try to see what failed
    import traceback
    traceback.print_exc()
    raise e
# Mocking the actual validator logic which likely calls ffmpeg

@pytest.fixture
def mock_subprocess():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout='{"streams": []}', stderr="")
        yield mock_run

def test_validator_missing_file():
    # Calling validate with a non-existent path
    # Should likely return a specific error struct or raise exception safely
    # For now, let's assume it should return a FAILED or ERROR status in JSON
    
    result = validate("non_existent_file.mp4")
    
    # Depending on implementation, it might vary, but let's check basic fields
    assert "status" in result
    assert result["status"] in ["ERROR", "FAILED"]

def test_validator_corrupt_file_mock(mock_subprocess):
    # Simulate FFmpeg failing to read file output
    mock_subprocess.side_effect = Exception("Invalid data found")
    
    # Create a dummy temp file
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(b"garbage content not a video")
        tmp_path = tmp.name
    
    try:
        result = validate(tmp_path)
        assert result["status"] == "ERROR"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_validator_valid_execution(mock_subprocess):
    # Mock successful loudnorm output
    # JSON output from ffprobe typically expected by some validators
    mock_subprocess.return_value.stdout = json.dumps({
        "input_i": "-23.0",
        "input_tp": "-1.5",
        "input_lra": "7.0",
        "input_thresh": "-33.0"
    })
    
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        result = validate(tmp_path)
        # Even with mock, ensuring code path validates return structure
        assert isinstance(result, dict)
        assert "status" in result
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

import json
