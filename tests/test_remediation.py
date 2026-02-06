import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add project root to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.remediation.fix_media import fix_loudness, fix_transcode, fix_combined

@pytest.fixture
def mock_subprocess():
    with patch("subprocess.run") as mock_run:
        # valid return
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        yield mock_run

def test_fix_loudness_command_structure(mock_subprocess):
    input_file = "in.mp4"
    output_file = "out.mp4"
    
    success = fix_loudness(input_file, output_file)
    
    assert success is True
    mock_subprocess.assert_called_once()
    
    args = mock_subprocess.call_args[0][0]
    # Check key flags
    assert "ffmpeg" in args
    assert "-af" in args
    assert "loudnorm=I=-23:LRA=7:tp=-1.5" in args
    assert output_file in args

def test_fix_transcode_command_structure(mock_subprocess):
    input_file = "in.mp4"
    output_file = "out.mp4"
    
    success = fix_transcode(input_file, output_file)
    
    assert success is True
    args = mock_subprocess.call_args[0][0]
    assert "-c:v" in args
    assert "libx264" in args
    assert "-crf" in args
    assert "18" in args
    assert "-preset" in args
    assert "slow" in args

def test_fix_combined_command_structure(mock_subprocess):
    input_file = "in.mp4"
    output_file = "out.mp4"
    
    success = fix_combined(input_file, output_file)
    
    assert success is True
    args = mock_subprocess.call_args[0][0]
    # Should have both audio filter and video codec settings
    assert "loudnorm=I=-23:LRA=7:tp=-1.5" in args
    assert "libx264" in args
    assert "-crf" in args
    assert "18" in args

def test_failure_handling():
    with patch("subprocess.run") as mock_run:
        # Simulate FFmpeg failure
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, ["ffmpeg"], stderr="Error")
        
        success = fix_loudness("in.mp4", "out.mp4")
        assert success is False
