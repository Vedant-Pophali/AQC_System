import React, { useEffect, useState } from 'react';
import { Grid, Button, Card, Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, CircularProgress, Fade } from '@mui/material';
import { TrendingUp, CheckCircle, ErrorOutline, Queue, ArrowForward } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import StatusCard from '../components/StatusCard';
import ProcessTerminal from '../components/ProcessTerminal';
import apiClient from '../api/client';
import { Job } from '../types';

const Home: React.FC = () => {
    const navigate = useNavigate();

    const { data: jobs = [], isLoading, error } = useQuery({
        queryKey: ['jobs'],
        queryFn: async () => {
            const response = await apiClient.get<Job[]>('/jobs');
            return response.data;
        },
        refetchInterval: 5000
    });

    const stats = React.useMemo(() => {
        const total = jobs.length;
        const completed = jobs.filter(j => j.status === 'COMPLETED').length;
        const failed = jobs.filter(j => j.status === 'FAILED').length;
        const passRate = total > 0 ? ((completed / total) * 100).toFixed(1) : '0';

        return [
            { label: "Total Files Processed", value: total.toString(), trend: 12, icon: Queue, status: 'primary' },
            { label: "Pass Rate", value: `${passRate}%`, trend: 5, icon: CheckCircle, status: 'success' },
            { label: "Critical Failures", value: failed.toString(), trend: -2, icon: ErrorOutline, status: 'danger' }
        ];
    }, [jobs]);

    return (
        <Fade in={true}>
            <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', mb: 4 }}>
                    <Box>
                        <Typography variant="h4" fontWeight="bold">Dashboard Overview</Typography>
                        <Typography variant="body1" color="text.secondary">Welcome back, QC Operator. System is ready.</Typography>
                    </Box>
                    <Button
                        variant="contained"
                        size="large"
                        endIcon={<ArrowForward />}
                        onClick={() => navigate('/dashboard')}
                    >
                        Start New QC Run
                    </Button>
                </Box>

                <Grid container spacing={4} sx={{ mb: 4 }}>
                    {stats.map((stat, idx) => (
                        <Grid key={idx} size={{ xs: 12, md: 4 }}>
                            <StatusCard {...stat} icon={stat.icon as any} />
                        </Grid>
                    ))}
                </Grid>

                <Grid container spacing={4}>
                    <Grid size={{ xs: 12, lg: 8 }}>
                        <Card sx={{ height: '100%', p: 0 }}>
                            <Box sx={{ p: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="h6">Recent Activity</Typography>
                                <Button variant="text" size="small" onClick={() => navigate('/reports')}>View All</Button>
                            </Box>
                            <TableContainer>
                                <Table>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell sx={{ color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.75rem' }}>File Name</TableCell>
                                            <TableCell sx={{ color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.75rem' }}>Format</TableCell>
                                            <TableCell align="right" sx={{ color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.75rem' }}>Status</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {isLoading ? (
                                            <TableRow><TableCell colSpan={3} align="center"><CircularProgress size={24} /></TableCell></TableRow>
                                        ) : jobs.length === 0 ? (
                                            <TableRow><TableCell colSpan={3} align="center" sx={{ color: 'text.secondary' }}>No activity yet.</TableCell></TableRow>
                                        ) : (
                                            jobs.slice(0, 5).map((job) => (
                                                <TableRow key={job.id} hover>
                                                    <TableCell>
                                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                                            <Box sx={{ bgcolor: 'action.hover', p: 1, borderRadius: 1 }}>
                                                                <TrendingUp color="primary" fontSize="small" />
                                                            </Box>
                                                            <Box>
                                                                <Typography variant="body2" fontWeight="medium" noWrap sx={{ maxWidth: 200 }}>
                                                                    {job.originalFilename}
                                                                </Typography>
                                                                <Typography variant="caption" color="text.secondary">
                                                                    {new Date(job.createdAt).toLocaleTimeString()}
                                                                </Typography>
                                                            </Box>
                                                        </Box>
                                                    </TableCell>
                                                    <TableCell>
                                                        <Chip label="MEDIA" size="small" variant="outlined" sx={{ borderRadius: 1 }} />
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        <Chip
                                                            label={job.status}
                                                            size="small"
                                                            color={job.status === 'COMPLETED' ? 'success' : job.status === 'FAILED' ? 'error' : 'warning'}
                                                            variant="outlined"
                                                        />
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        )}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </Card>
                    </Grid>
                    <Grid size={{ xs: 12, lg: 4 }}>
                        <Box sx={{ height: '100%' }}>
                            <ProcessTerminal
                                title="Live System Logs"
                                logs={[
                                    "System init complete...",
                                    "Connected to Database [OK]",
                                    "Monitoring uploads/ directory...",
                                    isLoading ? "Syncing with backend..." : "Sync Complete [OK]",
                                    !isLoading && jobs.length > 0 ? `Found ${jobs.length} total jobs.` : "Waiting for new tasks..."
                                ]}
                            />
                        </Box>
                    </Grid>
                </Grid>
            </Box>
        </Fade>
    );
};

export default Home;
