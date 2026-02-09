import React, { useState, useEffect } from 'react';
import { Row, Col, Container } from 'react-bootstrap'; // Layout grid from bootstrap (keeping for now as per plan, or switching to MUI Grid?)
// Plan said "Adopt Material UI". I'll switch to MUI Grid.
import { Grid, Box, Typography, Fade } from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import FileUploader from '../components/dashboard/FileUploader';
import AnalysisProgress from '../components/dashboard/AnalysisProgress';
import JobControls from '../components/dashboard/JobControls';
import ProcessTerminal from '../components/ProcessTerminal';
import toast, { Toaster } from 'react-hot-toast';

const Dashboard: React.FC = () => {
    const [activeJobId, setActiveJobId] = useState<string | null>(null);
    const [localLogs, setLocalLogs] = useState<string[]>([]);

    // Polling for Job Status
    const { data: jobData, error: jobError } = useQuery({
        queryKey: ['job', activeJobId],
        queryFn: async () => {
            if (!activeJobId) return null;
            const response = await apiClient.get(`/jobs/${activeJobId}`);
            return response.data;
        },
        enabled: !!activeJobId,
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            return (status === 'COMPLETED' || status === 'FAILED') ? false : 3000;
        }
    });

    const jobStatus = jobData?.status;
    const progress = jobStatus === 'COMPLETED' ? 100 : jobStatus === 'PROCESSING' ? 45 : 0; // Simplified progress for now, or use real progress from backend if available

    // Effect for logging status changes
    useEffect(() => {
        if (jobStatus) {
            setLocalLogs(prev => [...prev, `Job Status Update: ${jobStatus}`]);
            if (jobStatus === 'COMPLETED') {
                toast.success('Analysis Completed Successfully!');
                setLocalLogs(prev => [...prev, "Master Report generated."]);
            } else if (jobStatus === 'FAILED') {
                toast.error(`Analysis Failed: ${jobData?.errorMessage || 'Unknown error'}`);
                setLocalLogs(prev => [...prev, `Error: ${jobData?.errorMessage}`]);
            }
        }
    }, [jobStatus, jobData]);

    // Start Analysis Mutation
    const startMutation = useMutation({
        mutationFn: async ({ file, profile }: { file: File, profile: string }) => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('profile', profile);
            const response = await apiClient.post('/jobs', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            return response.data;
        },
        onMutate: () => {
            setLocalLogs(["Initializing QC Analysis Protocol...", "Uploading media..."]);
        },
        onSuccess: (data) => {
            setActiveJobId(data.id);
            setLocalLogs(prev => [...prev, `Job Created [ID: ${data.id}]`, "Handing off to ML Core engine..."]);
            toast.success('Upload Successful! Analysis Started.');
        },
        onError: (error: any) => {
            const msg = error.response?.data?.error || error.message || "Upload Failed";
            setLocalLogs(prev => [...prev, `Fatal: ${msg}`]);
            toast.error(msg);
        }
    });

    // Remediation Mutation
    const remediateMutation = useMutation({
        mutationFn: async (fixType: string) => {
            if (!activeJobId) throw new Error("No active job");
            await apiClient.post(`/jobs/${activeJobId}/fix`, { fixType });
        },
        onSuccess: () => {
            toast.success('Remediation Queued');
            setLocalLogs(prev => [...prev, "Remediation queued. Processing..."]);
        },
        onError: () => {
            toast.error('Failed to queue remediation');
            setLocalLogs(prev => [...prev, "Error triggering remediation."]);
        }
    });

    // Poll for remediation status if needed, or re-use job polling if it updates validation status?
    // Original code had a separate poll for fixStatus.
    // I can add another query or just rely on the job query if the job object contains fixStatus.
    // Assuming /jobs/:id returns fixStatus too.

    return (
        <Fade in={true}>
            <Container>
                <Toaster position="top-right" />
                <Box sx={{ mb: 4, mt: 2 }}>
                    <Typography variant="h4" fontWeight="bold">Run Quality Control</Typography>
                    <Typography variant="body1" color="text.secondary">Upload media to start the technical compliance pipeline.</Typography>
                </Box>

                <Grid container spacing={4}>
                    <Grid item xs={12} lg={6}>
                        <FileUploader
                            onStartAnalysis={(file, profile) => startMutation.mutate({ file, profile })}
                            isProcessing={startMutation.isPending || (jobStatus === 'PROCESSING')}
                        />
                    </Grid>

                    <Grid item xs={12} lg={6}>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4, height: '100%' }}>
                            <AnalysisProgress
                                progress={progress} // Improved progress logic can be added later
                                status={jobStatus}
                                jobId={activeJobId}
                            />

                            <JobControls
                                onRemediate={(type) => remediateMutation.mutate(type)}
                                jobStatus={jobStatus}
                            />

                            <Box sx={{ flexGrow: 1, minHeight: 250 }}>
                                <ProcessTerminal title="Forensic Analysis Logs" logs={localLogs} />
                            </Box>
                        </Box>
                    </Grid>
                </Grid>
            </Container>
        </Fade>
    );
};

export default Dashboard;
