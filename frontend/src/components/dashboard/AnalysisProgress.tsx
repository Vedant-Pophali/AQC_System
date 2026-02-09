import React from 'react';
import { Card, Typography, LinearProgress, Box, Chip, Button } from '@mui/material';
import { CheckCircle, ErrorOutline, PlayArrow, OpenInNew } from '@mui/icons-material';
import { config } from '../../config';

interface AnalysisProgressProps {
    progress: number;
    status: string; // 'STARTING', 'PROCESSING', 'COMPLETED', 'FAILED'
    jobId: string | null;
}

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({ progress, status, jobId }) => {
    const isCompleted = status === 'COMPLETED';
    const isFailed = status === 'FAILED';

    const getStatusColor = () => {
        if (isCompleted) return 'success';
        if (isFailed) return 'error';
        return 'primary';
    };

    return (
        <Card sx={{ p: 4, mb: 4 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box component="span" sx={{ bgcolor: 'primary.main', color: 'white', borderRadius: '50%', width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}>2</Box>
                Analysis Progress
            </Typography>

            {!jobId ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 5, color: 'text.secondary', opacity: 0.5 }}>
                    <PlayArrow sx={{ fontSize: 48, mb: 1 }} />
                    <Typography>Waiting for analysis to start...</Typography>
                </Box>
            ) : (
                <Box sx={{ py: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2" fontWeight="bold">Technical Compliance Pipeline</Typography>
                        <Typography variant="body2" color="text.secondary">{progress}%</Typography>
                    </Box>
                    <LinearProgress
                        variant="determinate"
                        value={progress}
                        color={getStatusColor()}
                        sx={{ height: 10, borderRadius: 5, mb: 3 }}
                    />

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="caption" color="text.secondary">Current Status</Typography>
                        <Chip
                            label={status || 'STARTING'}
                            color={getStatusColor()}
                            size="small"
                            variant="outlined"
                        />
                    </Box>

                    {isCompleted && (
                        <Button
                            variant="contained"
                            color="success"
                            fullWidth
                            sx={{ mt: 3 }}
                            startIcon={<CheckCircle />}
                            onClick={() => window.open(`${config.apiBaseUrl}/jobs/${jobId}/visual`, '_blank')}
                        >
                            View Full QC Report
                        </Button>
                    )}

                    {isFailed && (
                        <Box sx={{ mt: 2, p: 2, bgcolor: 'error.light', color: 'error.contrastText', borderRadius: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                            <ErrorOutline />
                            <Typography variant="body2">Analysis Failed. Check logs for details.</Typography>
                        </Box>
                    )}
                </Box>
            )}
        </Card>
    );
};

export default AnalysisProgress;
