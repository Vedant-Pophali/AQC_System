import React, { useState, useEffect } from 'react';
import { Box, Typography, Fade, Container, Stack } from '@mui/material';
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';
import { Job } from '../types';
import FileUploader from '../components/dashboard/FileUploader';
import AnalysisProgress from '../components/dashboard/AnalysisProgress';
import JobControls from '../components/dashboard/JobControls';
import ProcessTerminal from '../components/ProcessTerminal';
import toast, { Toaster } from 'react-hot-toast';

const Dashboard: React.FC = () => {
    const [activeJobId, setActiveJobId] = useState<string | null>(null);
    const [localLogs, setLocalLogs] = useState<string[]>([]);

    // Polling for Job Status
    const { data: jobData } = useQuery({
        queryKey: ['job', activeJobId],
        queryFn: async () => {
            if (!activeJobId) return null;
            const response = await apiClient.get<Job>(`/jobs/${activeJobId}`);
            return response.data;
        },
        enabled: !!activeJobId,
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            const fixStatus = query.state.data?.fixStatus;

            // Keep polling if job is processing OR if fix is processing
            if (status === 'PROCESSING' || status === 'STARTING') return 3000;
            if (fixStatus === 'PROCESSING') return 3000;

            return false;
        }
    });

    const jobStatus = jobData?.status;
    const fixStatus = jobData?.fixStatus;
    const progress = jobStatus === 'COMPLETED' ? 100 : jobStatus === 'PROCESSING' ? 45 : 0;

    // Effect for logging status changes
    useEffect(() => {
        if (jobStatus) {
            setLocalLogs(prev => [...prev, `Job Status Update: ${jobStatus}`]);
            if (jobStatus === 'COMPLETED' && !localLogs.includes("Master Report generated.")) {
                toast.success('Analysis Completed Successfully!');
                setLocalLogs(prev => [...prev, "Master Report generated."]);
            } else if (jobStatus === 'FAILED' && !localLogs.includes(`Error: ${jobData?.errorMessage}`)) {
                toast.error(`Analysis Failed: ${jobData?.errorMessage || 'Unknown error'}`);
                setLocalLogs(prev => [...prev, `Error: ${jobData?.errorMessage}`]);
            }
        }
    }, [jobStatus, jobData, localLogs]);

    // Effect for logging fix status changes
    useEffect(() => {
        if (fixStatus) {
            if (fixStatus === 'PROCESSING' && !localLogs.includes("Remediation in progress...")) {
                setLocalLogs(prev => [...prev, "Remediation engine started...", "Applying EBU R128 normalization..."]);
            }
            if (fixStatus === 'COMPLETED' && !localLogs.includes("Remediation Complete.")) {
                toast.success('Remediation Completed!');
                setLocalLogs(prev => [...prev, "Remediation Complete.", "Fixed file ready for download."]);
            }
        }
    }, [fixStatus, localLogs]);

    const handleDownloadFixed = async () => {
        if (!activeJobId) return;
        try {
            const downloadUrl = `${apiClient.defaults.baseURL}/jobs/${activeJobId}/download-fixed`;
            window.open(downloadUrl, '_blank');
            setLocalLogs(prev => [...prev, "Downloading fixed asset..."]);
        } catch (err) {
            toast.error("Download failed");
        }
    };

    const startMutation = useMutation({
        mutationFn: async ({ file, profile }: { file: File, profile: string }) => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('profile', profile);
            const response = await apiClient.post<Job>('/jobs', formData, {
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

    return (
        <Fade in={true}>
            <Container maxWidth="xl">
                <Toaster position="top-right" />
                <Box sx={{ mb: 4, mt: 2 }}>
                    <Typography variant="h4" fontWeight="bold">Run Quality Control</Typography>
                    <Typography variant="body1" color="text.secondary">Upload media to start the technical compliance pipeline.</Typography>
                </Box>

                <Box sx={{ display: 'flex', flexDirection: { xs: 'column', lg: 'row' }, gap: 4 }}>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <FileUploader
                            onStartAnalysis={(file, profile) => startMutation.mutate({ file, profile })}
                            isProcessing={startMutation.isPending || (jobStatus === 'PROCESSING')}
                        />
                    </Box>

                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Stack spacing={4} sx={{ height: '100%' }}>
                            <AnalysisProgress
                                progress={progress}
                                status={jobStatus || 'STARTING'}
                                jobId={activeJobId}
                            />

                            <JobControls
                                onRemediate={(type) => remediateMutation.mutate(type)}
                                onDownload={handleDownloadFixed}
                                jobStatus={jobStatus || 'STARTING'}
                                fixStatus={fixStatus}
                                isRemediating={remediateMutation.isPending || fixStatus === 'PROCESSING'}
                            />

                            <Box sx={{ flexGrow: 1, minHeight: 250 }}>
                                <ProcessTerminal title="Forensic Analysis Logs" logs={localLogs} />
                            </Box>
                        </Stack>
                    </Box>
                </Box>
            </Container>
        </Fade>
    );
};

export default Dashboard;
