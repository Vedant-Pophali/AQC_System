import React, { useState } from 'react';
import {
    Box,
    Card,
    Typography,
    Button,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Stack,
    CircularProgress
} from '@mui/material';
import { CloudUpload, PlayArrow, CheckCircle } from '@mui/icons-material';

interface FileUploaderProps {
    onStartAnalysis: (file: File, profile: string) => void;
    isProcessing: boolean;
}

const FileUploader: React.FC<FileUploaderProps> = ({ onStartAnalysis, isProcessing }) => {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [profile, setProfile] = useState<string>('netflix_hd');

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            setSelectedFile(event.target.files[0]);
        }
    };

    const handleStartKey = () => {
        if (selectedFile) {
            onStartAnalysis(selectedFile, profile);
        }
    };

    return (
        <Card sx={{ p: 4, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box component="span" sx={{ bgcolor: 'primary.main', color: 'white', borderRadius: '50%', width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}>1</Box>
                Select Source Media
            </Typography>

            <Box
                sx={{
                    border: '2px dashed',
                    borderColor: selectedFile ? 'primary.main' : 'grey.300',
                    borderRadius: 4,
                    p: 4,
                    textAlign: 'center',
                    mb: 3,
                    position: 'relative',
                    bgcolor: selectedFile ? 'primary.main' : 'transparent',
                    backgroundColor: selectedFile ? 'rgba(25, 118, 210, 0.08)' : 'transparent',
                    transition: 'all 0.2s',
                    cursor: isProcessing ? 'default' : 'pointer',
                    '&:hover': {
                        borderColor: 'primary.main',
                        backgroundColor: 'rgba(25, 118, 210, 0.04)'
                    }
                }}
            >
                <input
                    type="file"
                    onChange={handleFileChange}
                    disabled={isProcessing}
                    accept=".mp4,.mxf,.mov,.mkv"
                    style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        opacity: 0,
                        cursor: 'inherit'
                    }}
                />

                <Box sx={{ pointerEvents: 'none' }}>
                    <Box sx={{
                        display: 'inline-flex',
                        p: 2,
                        borderRadius: '50%',
                        bgcolor: selectedFile ? 'primary.main' : 'grey.100',
                        color: selectedFile ? 'white' : 'primary.main',
                        mb: 2
                    }}>
                        {selectedFile ? <CheckCircle fontSize="large" /> : <CloudUpload fontSize="large" />}
                    </Box>
                    <Typography variant="subtitle1" fontWeight="bold">
                        {selectedFile ? selectedFile.name : "Drag & Drop or Click to Upload"}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        Supports MP4, MXF, MOV, MKV
                    </Typography>
                </Box>
            </Box>

            {selectedFile && (
                <Box sx={{ bgcolor: 'background.paper', p: 2, borderRadius: 2, mb: 3, border: 1, borderColor: 'divider' }}>
                    <Stack direction="row" justifyContent="space-between" mb={2}>
                        <Typography variant="body2" color="text.secondary">Size</Typography>
                        <Typography variant="body2" fontWeight="bold">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</Typography>
                    </Stack>

                    <FormControl fullWidth size="small">
                        <InputLabel>Compliance Profile</InputLabel>
                        <Select
                            value={profile}
                            label="Compliance Profile"
                            onChange={(e) => setProfile(e.target.value)}
                            disabled={isProcessing}
                        >
                            <MenuItem value="strict">Strict (Gold Standard)</MenuItem>
                            <MenuItem value="netflix_hd">Netflix HD (Interoperable)</MenuItem>
                            <MenuItem value="youtube">YouTube (Web Optimized)</MenuItem>
                        </Select>
                    </FormControl>
                </Box>
            )}

            <Box sx={{ mt: 'auto' }}>
                <Button
                    variant="contained"
                    size="large"
                    fullWidth
                    onClick={handleStartKey}
                    disabled={!selectedFile || isProcessing}
                    startIcon={isProcessing ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
                >
                    {isProcessing ? "Processing..." : "Initialize Analysis"}
                </Button>
            </Box>
        </Card>
    );
};

export default FileUploader;
