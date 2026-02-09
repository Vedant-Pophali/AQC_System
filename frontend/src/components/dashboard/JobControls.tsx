import React from 'react';
import { Card, Typography, Button, Box } from '@mui/material';
import { AutoFixHigh } from '@mui/icons-material';

interface JobControlsProps {
    onRemediate: (type: string) => void;
    jobStatus: string;
}

const JobControls: React.FC<JobControlsProps> = ({ onRemediate, jobStatus }) => {
    if (jobStatus !== 'COMPLETED') return null;

    return (
        <Card sx={{ p: 4, mb: 4, animation: 'fadeIn 0.5s' }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box component="span" sx={{ bgcolor: 'warning.main', color: 'black', borderRadius: '50%', width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}>3</Box>
                Correction & Delivery
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Button
                    variant="outlined"
                    color="success"
                    size="large"
                    startIcon={<AutoFixHigh />}
                    onClick={() => onRemediate("combined_fix")}
                >
                    Remediate Audio Loudness & Video Artifacts
                </Button>
                <Typography variant="caption" color="text.secondary" align="center">
                    Applies EBU R128 Norm (-23 LUFS) + HQ Transcode. Auto-downloads to your machine.
                </Typography>
            </Box>
        </Card>
    );
};

export default JobControls;
