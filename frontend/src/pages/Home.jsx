import React, { useEffect, useState } from 'react';
import { Row, Col, Button, Card, Spinner } from 'react-bootstrap';
import { MdTrendingUp, MdCheckCircle, MdError, MdQueue, MdArrowForward } from 'react-icons/md';
import { useNavigate } from 'react-router-dom';
import StatusCard from '../components/StatusCard';
import ProcessTerminal from '../components/ProcessTerminal';
import apiClient from '../api/client';

const Home = () => {
    const navigate = useNavigate();
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState([
        { label: "Total Files Processed", value: "0", trend: 0, icon: MdQueue, status: 'primary' },
        { label: "Pass Rate", value: "0%", trend: 0, icon: MdCheckCircle, status: 'success' },
        { label: "Critical Failures", value: "0", trend: 0, icon: MdError, status: 'danger' }
    ]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await apiClient.get('/jobs');
                const allJobs = response.data;
                setJobs(allJobs);

                // Calculate Stats
                const total = allJobs.length;
                const completed = allJobs.filter(j => j.status === 'COMPLETED').length;
                const failed = allJobs.filter(j => j.status === 'FAILED').length;
                const passRate = total > 0 ? ((completed / total) * 100).toFixed(1) : 0;

                setStats([
                    { label: "Total Files Processed", value: total.toString(), trend: 0, icon: MdQueue, status: 'primary' },
                    { label: "Pass Rate", value: `${passRate}%`, trend: 0, icon: MdCheckCircle, status: 'success' },
                    { label: "Critical Failures", value: failed.toString(), trend: 0, icon: MdError, status: 'danger' }
                ]);
            } catch (err) {
                console.error("Home data fetch failed:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    return (
        <div className="fade-in">
            <div className="d-flex justify-content-between align-items-end mb-4">
                <div>
                    <h2 className="mb-1">Dashboard Overview</h2>
                    <p className="text-secondary mb-0">Welcome back, QC Operator. System is ready.</p>
                </div>
                <Button
                    variant="primary"
                    className="d-flex align-items-center gap-2 px-4 py-2"
                    onClick={() => navigate('/dashboard')}
                >
                    <span>Start New QC Run</span>
                    <MdArrowForward />
                </Button>
            </div>

            <Row className="g-4 mb-4">
                {stats.map((stat, idx) => (
                    <Col key={idx} xs={12} md={4}>
                        <StatusCard {...stat} />
                    </Col>
                ))}
            </Row>

            <Row className="g-4">
                <Col xs={12} lg={8}>
                    <Card className="glass-panel border-0 h-100 p-4">
                        <div className="d-flex justify-content-between align-items-center mb-4">
                            <h5 className="mb-0">Recent Activity</h5>
                            <Button variant="outline-secondary" size="sm" onClick={() => navigate('/reports')}>View All</Button>
                        </div>
                        <div className="table-responsive">
                            <table className="table table-dark table-hover mb-0 align-middle">
                                <thead>
                                    <tr>
                                        <th className="text-secondary text-uppercase small" style={{ width: '40%' }}>File Name</th>
                                        <th className="text-secondary text-uppercase small">Format</th>
                                        <th className="text-secondary text-uppercase small text-end">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {loading ? (
                                        <tr><td colSpan="3" className="text-center py-4"><Spinner size="sm" /></td></tr>
                                    ) : jobs.length === 0 ? (
                                        <tr><td colSpan="3" className="text-center py-4 text-secondary">No activity yet.</td></tr>
                                    ) : (
                                        jobs.slice(0, 5).map(job => (
                                            <tr key={job.id}>
                                                <td>
                                                    <div className="d-flex align-items-center gap-3">
                                                        <div className="bg-primary bg-opacity-10 p-2 rounded">
                                                            <MdTrendingUp className="text-primary" />
                                                        </div>
                                                        <div>
                                                            <div className="fw-medium text-truncate" style={{ maxWidth: '200px' }}>{job.originalFilename}</div>
                                                            <div className="small text-secondary">{new Date(job.createdAt).toLocaleTimeString()}</div>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td><span className="badge bg-secondary bg-opacity-25 text-secondary border border-secondary border-opacity-25 uppercase">Media</span></td>
                                                <td className="text-end">
                                                    <span className={`badge bg-${job.status === 'COMPLETED' ? 'success' : job.status === 'FAILED' ? 'danger' : 'warning'} bg-opacity-25 text-${job.status === 'COMPLETED' ? 'success' : job.status === 'FAILED' ? 'danger' : 'warning'} border border-${job.status === 'COMPLETED' ? 'success' : job.status === 'FAILED' ? 'danger' : 'warning'} border-opacity-25 small`}>
                                                        {job.status}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </Card>
                </Col>
                <Col xs={12} lg={4}>
                    <ProcessTerminal
                        title="Live System Logs"
                        logs={[
                            "System init complete...",
                            "Connected to Database [OK]",
                            "Monitoring uploads/ directory...",
                            loading ? "Syncing with backend..." : "Sync Complete [OK]",
                            !loading && jobs.length > 0 ? `Found ${jobs.length} total jobs.` : "Waiting for new tasks..."
                        ]}
                    />
                </Col>
            </Row>
        </div>
    );
};

export default Home;
