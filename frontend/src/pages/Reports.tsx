import React, { useState } from 'react';
import { Card, Button, Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Checkbox, IconButton, Chip, CircularProgress, Fade, Tooltip } from '@mui/material';
import { Download, Visibility, Delete, OpenInNew, Refresh } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import { Job } from '../types';
import toast from 'react-hot-toast';

const Reports: React.FC = () => {
    const queryClient = useQueryClient();
    const [selectedJobs, setSelectedJobs] = useState<string[]>([]);

    // Fetch Jobs
    const { data: jobs = [], isLoading } = useQuery({
        queryKey: ['jobs'],
        queryFn: async () => {
            const response = await apiClient.get<Job[]>('/jobs');
            return response.data;
        }
    });

    // Delete Job Mutation
    const deleteMutation = useMutation({
        mutationFn: async (jobId: string) => {
            await apiClient.delete(`/jobs/${jobId}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            toast.success('Job deleted successfully');
        },
        onError: () => toast.error('Failed to delete job')
    });

    // Bulk Delete Mutation
    const bulkDeleteMutation = useMutation({
        mutationFn: async (jobIds: string[]) => {
            await apiClient.delete('/jobs/batch', { data: jobIds });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            setSelectedJobs([]);
            toast.success('Selected jobs deleted successfully');
        },
        onError: () => toast.error('Failed to delete selected jobs')
    });

    const handleDownloadJson = async (jobId: string, filename: string) => {
        try {
            const response = await apiClient.get(`/jobs/${jobId}/report`);
            const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `AQC_Report_${jobId}.json`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error("Download failed:", err);
            toast.error("Failed to download report JSON.");
        }
    };

    const handleSelectAll = (checked: boolean) => {
        if (checked) {
            setSelectedJobs(jobs.map(job => job.id));
        } else {
            setSelectedJobs([]);
        }
    };

    const handleSelectJob = (jobId: string) => {
        setSelectedJobs(prev =>
            prev.includes(jobId)
                ? prev.filter(id => id !== jobId)
                : [...prev, jobId]
        );
    };

    const handleBulkOpen = () => {
        selectedJobs.forEach(jobId => {
            const url = `${apiClient.defaults.baseURL}/jobs/${jobId}/visual`;
            window.open(url, '_blank');
        });
    };

    return (
        <Fade in={true}>
            <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', mb: 4 }}>
                    <Box>
                        <Typography variant="h4" fontWeight="bold">Quality Reports</Typography>
                        <Typography variant="body1" color="text.secondary">Archive of compliance certificates and failure logs.</Typography>
                    </Box>
                    <Button
                        variant="outlined"
                        startIcon={<Refresh />}
                        onClick={() => queryClient.invalidateQueries({ queryKey: ['jobs'] })}
                    >
                        Refresh
                    </Button>
                </Box>

                {selectedJobs.length > 0 && (
                    <Card sx={{ mb: 3, bgcolor: 'primary.main', color: 'primary.contrastText', p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Chip label={`${selectedJobs.length} selected`} color="default" sx={{ bgcolor: 'white', color: 'primary.main', fontWeight: 'bold' }} />
                            <Typography variant="body2">Bulk Actions:</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                                variant="contained"
                                color="secondary"
                                size="small"
                                startIcon={<OpenInNew />}
                                onClick={handleBulkOpen}
                            >
                                Open All
                            </Button>
                            <Button
                                variant="contained"
                                color="error"
                                size="small"
                                startIcon={<Delete />}
                                onClick={() => {
                                    if (window.confirm(`Delete ${selectedJobs.length} items?`)) {
                                        bulkDeleteMutation.mutate(selectedJobs);
                                    }
                                }}
                            >
                                Delete Selected
                            </Button>
                            <Button color="inherit" onClick={() => setSelectedJobs([])}>Cancel</Button>
                        </Box>
                    </Card>
                )}

                <Card>
                    <TableContainer>
                        <Table>
                            <TableHead>
                                <TableRow>
                                    <TableCell padding="checkbox">
                                        <Checkbox
                                            checked={jobs.length > 0 && selectedJobs.length === jobs.length}
                                            indeterminate={selectedJobs.length > 0 && selectedJobs.length < jobs.length}
                                            onChange={(e) => handleSelectAll(e.target.checked)}
                                        />
                                    </TableCell>
                                    <TableCell>Job ID</TableCell>
                                    <TableCell>File Name</TableCell>
                                    <TableCell>Date</TableCell>
                                    <TableCell>Status</TableCell>
                                    <TableCell align="right">Actions</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {isLoading ? (
                                    <TableRow><TableCell colSpan={6} align="center"><CircularProgress /></TableCell></TableRow>
                                ) : jobs.length === 0 ? (
                                    <TableRow><TableCell colSpan={6} align="center" sx={{ color: 'text.secondary', py: 4 }}>No reports found.</TableCell></TableRow>
                                ) : (
                                    jobs.map((job) => (
                                        <TableRow key={job.id} selected={selectedJobs.includes(job.id)} hover>
                                            <TableCell padding="checkbox">
                                                <Checkbox
                                                    checked={selectedJobs.includes(job.id)}
                                                    onChange={() => handleSelectJob(job.id)}
                                                />
                                            </TableCell>
                                            <TableCell sx={{ fontFamily: 'monospace' }}>#{job.id.substring(0, 8)}...</TableCell>
                                            <TableCell>{job.originalFilename || "Unnamed"}</TableCell>
                                            <TableCell>{new Date(job.createdAt).toLocaleDateString()}</TableCell>
                                            <TableCell>
                                                <Chip
                                                    label={job.status}
                                                    size="small"
                                                    color={job.status === 'COMPLETED' ? 'success' : job.status === 'FAILED' ? 'error' : 'warning'}
                                                    variant="outlined"
                                                />
                                            </TableCell>
                                            <TableCell align="right">
                                                <Tooltip title="View Report">
                                                    <span>
                                                        <IconButton
                                                            size="small"
                                                            onClick={() => window.open(`${apiClient.defaults.baseURL}/jobs/${job.id}/visual`, '_blank')}
                                                            disabled={job.status !== 'COMPLETED'}
                                                        >
                                                            <Visibility />
                                                        </IconButton>
                                                    </span>
                                                </Tooltip>
                                                <Tooltip title="Download JSON">
                                                    <span>
                                                        <IconButton
                                                            size="small"
                                                            onClick={() => handleDownloadJson(job.id, job.originalFilename)}
                                                            disabled={job.status !== 'COMPLETED'}
                                                        >
                                                            <Download />
                                                        </IconButton>
                                                    </span>
                                                </Tooltip>
                                                <Tooltip title="Delete">
                                                    <IconButton
                                                        size="small"
                                                        color="error"
                                                        onClick={() => {
                                                            if (window.confirm('Delete this job?')) deleteMutation.mutate(job.id);
                                                        }}
                                                    >
                                                        <Delete />
                                                    </IconButton>
                                                </Tooltip>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Card>
            </Box>
        </Fade>
    );
};

export default Reports;
