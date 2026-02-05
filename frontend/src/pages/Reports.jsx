import React, { useEffect, useState } from 'react';
import { Card, Button, Spinner, Form, Badge } from 'react-bootstrap';
import { MdDownload, MdVisibility, MdDelete, MdOpenInNew } from 'react-icons/md';
import apiClient from '../api/client';

const Reports = () => {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedJobs, setSelectedJobs] = useState([]);

    const fetchJobs = async () => {
        try {
            const response = await apiClient.get('/jobs');
            setJobs(response.data);
        } catch (err) {
            console.error("Failed to fetch reports:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchJobs();
    }, []);

    const handleViewReport = (jobId) => {
        const url = `${apiClient.defaults.baseURL}/jobs/${jobId}/visual`;
        window.open(url, '_blank');
    };

    const handleDownloadJson = async (jobId, filename) => {
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
            alert("Failed to download report JSON.");
        }
    };

    const handleDeleteJob = async (jobId) => {
        if (!window.confirm("Are you sure you want to delete this job and all associated files? This action cannot be undone.")) {
            return;
        }

        try {
            await apiClient.delete(`/jobs/${jobId}`);
            setJobs(jobs.filter(job => job.id !== jobId));
            setSelectedJobs(selectedJobs.filter(id => id !== jobId));
        } catch (err) {
            console.error("Delete failed:", err);
            alert("Failed to delete job.");
        }
    };

    const handleSelectJob = (jobId) => {
        setSelectedJobs(prev =>
            prev.includes(jobId)
                ? prev.filter(id => id !== jobId)
                : [...prev, jobId]
        );
    };

    const handleSelectAll = (e) => {
        if (e.target.checked) {
            setSelectedJobs(jobs.map(job => job.id));
        } else {
            setSelectedJobs([]);
        }
    };

    const handleBulkDelete = async () => {
        if (!window.confirm(`Are you sure you want to delete ${selectedJobs.length} selected jobs and their files?`)) {
            return;
        }

        try {
            await apiClient.delete('/jobs/batch', { data: selectedJobs });
            setJobs(jobs.filter(job => !selectedJobs.includes(job.id)));
            setSelectedJobs([]);
        } catch (err) {
            console.error("Bulk delete failed:", err);
            alert("Failed to delete selected jobs.");
        }
    };

    const handleBulkOpen = () => {
        selectedJobs.forEach(jobId => {
            const url = `${apiClient.defaults.baseURL}/jobs/${jobId}/visual`;
            window.open(url, '_blank');
        });
    };

    return (
        <div className="fade-in">
            <div className="d-flex justify-content-between align-items-end mb-4">
                <div>
                    <h2 className="mb-1">Quality Reports</h2>
                    <p className="text-secondary mb-0">Archive of compliance certificates and failure logs.</p>
                </div>
                <div className="d-flex gap-2">
                    <Button variant="outline-primary" size="sm" onClick={fetchJobs}>Refresh</Button>
                </div>
            </div>

            {selectedJobs.length > 0 && (
                <Card className="glass-panel border-0 mb-3 bg-primary bg-opacity-10 border-primary border-opacity-25 shadow-sm">
                    <Card.Body className="py-2 px-4 d-flex align-items-center justify-content-between">
                        <div className="d-flex align-items-center">
                            <Badge bg="primary" className="me-3">{selectedJobs.length} selected</Badge>
                            <span className="text-light small">Bulk actions:</span>
                        </div>
                        <div className="d-flex gap-2">
                            <Button
                                variant="link"
                                className="text-decoration-none text-light p-0 px-2 small d-flex align-items-center"
                                onClick={handleBulkOpen}
                            >
                                <MdOpenInNew size={16} className="me-1" /> Open All
                            </Button>
                            <Button
                                variant="link"
                                className="text-decoration-none text-danger p-0 px-2 small d-flex align-items-center"
                                onClick={handleBulkDelete}
                            >
                                <MdDelete size={16} className="me-1" /> Delete Selected
                            </Button>
                            <Button
                                variant="link"
                                className="text-decoration-none text-secondary p-0 px-2 small"
                                onClick={() => setSelectedJobs([])}
                            >
                                Cancel
                            </Button>
                        </div>
                    </Card.Body>
                </Card>
            )}

            <Card className="glass-panel border-0">
                <div className="table-responsive">
                    <table className="table table-dark table-hover mb-0 align-middle">
                        <thead>
                            <tr className="border-bottom border-secondary border-opacity-25">
                                <th className="py-3 ps-4" style={{ width: '40px' }}>
                                    <Form.Check
                                        type="checkbox"
                                        checked={selectedJobs.length === jobs.length && jobs.length > 0}
                                        onChange={handleSelectAll}
                                    />
                                </th>
                                <th className="py-3 text-secondary text-uppercase small">Job ID</th>
                                <th className="py-3 text-secondary text-uppercase small">File Name</th>
                                <th className="py-3 text-secondary text-uppercase small">Date</th>
                                <th className="py-3 text-secondary text-uppercase small">Status</th>
                                <th className="py-3 pe-4 text-end text-secondary text-uppercase small">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr>
                                    <td colSpan="6" className="text-center py-5">
                                        <Spinner animation="border" variant="primary" size="sm" className="me-2" />
                                        <span className="text-secondary">Loading reports...</span>
                                    </td>
                                </tr>
                            ) : jobs.length === 0 ? (
                                <tr>
                                    <td colSpan="6" className="text-center py-5 text-secondary">No reports found. Start a QC job to see results here.</td>
                                </tr>
                            ) : (
                                jobs.map((job) => (
                                    <tr key={job.id} className={selectedJobs.includes(job.id) ? 'bg-primary bg-opacity-10' : ''}>
                                        <td className="ps-4">
                                            <Form.Check
                                                type="checkbox"
                                                checked={selectedJobs.includes(job.id)}
                                                onChange={() => handleSelectJob(job.id)}
                                            />
                                        </td>
                                        <td className="text-monospace text-secondary small">#{job.id}</td>
                                        <td className="fw-medium">{job.originalFilename || "Unnamed Job"}</td>
                                        <td className="text-secondary small">{new Date(job.createdAt).toLocaleDateString()}</td>
                                        <td>
                                            <span className={`badge bg-${job.status === 'COMPLETED' ? 'success' : job.status === 'FAILED' ? 'danger' : 'warning'} bg-opacity-25 text-${job.status === 'COMPLETED' ? 'success' : job.status === 'FAILED' ? 'danger' : 'warning'} border border-${job.status === 'COMPLETED' ? 'success' : job.status === 'FAILED' ? 'danger' : 'warning'} border-opacity-25`}>
                                                {job.status}
                                            </span>
                                        </td>
                                        <td className="pe-4 text-end">
                                            <Button
                                                variant="link"
                                                className="text-decoration-none text-light p-0 me-3"
                                                title="View Report"
                                                onClick={() => handleViewReport(job.id)}
                                                disabled={job.status !== 'COMPLETED'}
                                            >
                                                <MdVisibility size={18} />
                                            </Button>
                                            <Button
                                                variant="link"
                                                className="text-decoration-none text-secondary p-0 me-3"
                                                title="Download JSON"
                                                onClick={() => handleDownloadJson(job.id, job.originalFilename)}
                                                disabled={job.status !== 'COMPLETED'}
                                            >
                                                <MdDownload size={18} />
                                            </Button>
                                            <Button
                                                variant="link"
                                                className="text-decoration-none text-danger p-0"
                                                title="Delete Job"
                                                onClick={() => handleDeleteJob(job.id)}
                                            >
                                                <MdDelete size={18} />
                                            </Button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </Card>
        </div>
    );
};

export default Reports;
