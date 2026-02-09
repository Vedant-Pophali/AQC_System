import React from 'react';
import { Card, Typography, Button, Box, CircularProgress } from '@mui/material';
import { AutoFixHigh, Download } from '@mui/icons-material';

interface JobControlsProps {
    onRemediate: (type: string) => void;
    onDownload: () => void;
    jobStatus: string;
    fixStatus?: string; // Additional prop for fix status
    isRemediating: boolean; // Loading state
}

const JobControls: React.FC<JobControlsProps> = ({ onRemediate, onDownload, jobStatus, fixStatus, isRemediating }) => {
    if (jobStatus !== 'COMPLETED') return null;

    return (
        <Card sx={{ p: 4, mb: 4, animation: 'fadeIn 0.5s' }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box component="span" sx={{ bgcolor: 'warning.main', color: 'black', borderRadius: '50%', width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}>3</Box>
                Correction & Delivery
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {!fixStatus || fixStatus === 'NONE' ? (
                    <Button
                        variant="outlined"
                        color="success"
                        size="large"
                        startIcon={isRemediating ? <CircularProgress size={20} /> : <AutoFixHigh />}
                        onClick={() => onRemediate("combined_fix")}
                        disabled={isRemediating}
                    >
                        {isRemediating ? "Remediating..." : "Remediate Audio Loudness & Video Artifacts"}
                    </Button>
                ) : fixStatus === 'PROCESSING' ? (
                    <Button variant="outlined" color="warning" disabled startIcon={<CircularProgress size={20} />}>
                        Processing Fix...
                    </Button>
                ) : fixStatus === 'COMPLETED' ? (
                    <Button
                        variant="contained"
                        color="success"
                        size="large"
                        startIcon={<Download />}
                        onClick={onDownload}
                    >
                        Download Fixed Version
                    </Button>
                ) : (
                    <Button variant="outlined" color="error" disabled>
                        Remediation Failed
                    </Button>
                )}

                <Typography variant="caption" color="text.secondary" align="center">
                    Applies EBU R128 Norm (-23 LUFS) + HQ Transcode. Auto-downloads to your machine.
                </Typography>
            </Box>
        </Card>
    );
};

export default JobControls;
