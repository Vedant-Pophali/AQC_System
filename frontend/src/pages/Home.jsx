import React from 'react';
import { Row, Col, Button, Card } from 'react-bootstrap';
import { MdTrendingUp, MdCheckCircle, MdError, MdQueue, MdArrowForward } from 'react-icons/md';
import { useNavigate } from 'react-router-dom';
import StatusCard from '../components/StatusCard';
import ProcessTerminal from '../components/ProcessTerminal';

const Home = () => {
    const navigate = useNavigate();

    // Mock data for initial view
    const stats = [
        { label: "Total Files Processed", value: "1,248", trend: 12, icon: MdQueue, status: 'primary' },
        { label: "Pass Rate", value: "98.2%", trend: 0.5, icon: MdCheckCircle, status: 'success' },
        { label: "Critical Failures", value: "24", trend: -5, icon: MdError, status: 'danger' }
    ];

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
                            <Button variant="outline-secondary" size="sm">View All</Button>
                        </div>
                        <div className="table-responsive">
                            <table className="table table-dark table-hover mb-0 align-middle">
                                <thead>
                                    <tr>
                                        <th className="text-secondary text-uppercase small" style={{ width: '40%' }}>File Name</th>
                                        <th className="text-secondary text-uppercase small">Format</th>
                                        <th className="text-secondary text-uppercase small">Duration</th>
                                        <th className="text-secondary text-uppercase small text-end">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {[1, 2, 3, 4].map(i => (
                                        <tr key={i}>
                                            <td>
                                                <div className="d-flex align-items-center gap-3">
                                                    <div className="bg-primary bg-opacity-10 p-2 rounded">
                                                        <MdTrendingUp className="text-primary" />
                                                    </div>
                                                    <div>
                                                        <div className="fw-medium">PROD_S01E0{i}_MSTR.mxf</div>
                                                        <div className="small text-secondary">Added 2 hours ago</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td><span className="badge bg-secondary bg-opacity-25 text-secondary border border-secondary border-opacity-25">MXF OP1a</span></td>
                                            <td className="text-monospace small">00:42:15:12</td>
                                            <td className="text-end">
                                                <span className="badge bg-success bg-opacity-25 text-success border border-success border-opacity-25 dot-indicator">
                                                    PASSED
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
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
                            "Loaded ML Models (BRISQUE) [OK]",
                            "Waiting for jobs..."
                        ]}
                    />
                </Col>
            </Row>
        </div>
    );
};

export default Home;
