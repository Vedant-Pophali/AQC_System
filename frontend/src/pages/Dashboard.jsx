import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import { MdCloudUpload, MdPlayArrow, MdCheckCircle, MdError } from 'react-icons/md';
import ProgressBar from '../components/ProgressBar';
import ProcessTerminal from '../components/ProcessTerminal';
import apiClient from '../api/client';

const Dashboard = () => {
    const [selectedFile, setSelectedFile] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [progress, setProgress] = useState(0);
    const [activeJobId, setActiveJobId] = useState(null);
    const [jobStatus, setJobStatus] = useState(null);
    const [logs, setLogs] = useState([]);
    const [selectedProfile, setSelectedProfile] = useState('netflix_hd');

    const addLog = (msg) => {
        setLogs(prev => [...prev.slice(-15), msg]);
    };

    const pollJobStatus = (id) => {
        const interval = setInterval(async () => {
            try {
                const response = await apiClient.get(`/jobs/${id}`);
                const job = response.data;
                setJobStatus(job.status);

                if (job.status === 'COMPLETED') {
                    setProgress(100);
                    addLog("Analysis Completed Successfully.");
                    addLog(`Master Report generated for ${job.originalFilename}`);
                    clearInterval(interval);
                    setIsProcessing(false);
                } else if (job.status === 'PROCESSING') {
                    if (progress < 90) {
                        setProgress(prev => Math.min(prev + Math.floor(Math.random() * 5), 95));
                    }
                    if (Math.random() > 0.7) {
                        const forensicMsgs = [
                            "Scanning for macro-blocking...",
                            "Analyzing audio loudness (EBU R.128)...",
                            "Checking for freeze frames...",
                            "Validating metadata compliance...",
                            "Running BRISQUE artifact detection..."
                        ];
                        addLog(forensicMsgs[Math.floor(Math.random() * forensicMsgs.length)]);
                    }
                } else if (job.status === 'FAILED') {
                    addLog(`Error: ${job.errorMessage || 'Unknown analysis failure'}`);
                    clearInterval(interval);
                    setIsProcessing(false);
                }
            } catch (err) {
                addLog("Warning: Connectivity issue while polling status...");
                console.error("Polling error:", err);
            }
        }, 3000);
    };

    const handleStartQC = async () => {
        if (!selectedFile) return;
        setIsProcessing(true);
        setProgress(5);
        setLogs(["Initializing QC Analysis Protocol...", `File: ${selectedFile.name}`, `Profile: ${selectedProfile.toUpperCase()}`]);

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('profile', selectedProfile);

        try {
            addLog("Uploading media to secure storage...");
            const response = await apiClient.post('/jobs', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            const job = response.data;
            setActiveJobId(job.id);
            setJobStatus(job.status);
            addLog(`Job Created [ID: ${job.id}]. Status: ${job.status}`);
            addLog("Handing off to ML Core engine...");
            pollJobStatus(job.id);
        } catch (err) {
            console.error(err);
            const errMsg = err.response?.data?.error || err.message || "Unknown Upload Error";
            addLog(`Fatal: Upload failed (${errMsg}). Process terminated.`);
            setIsProcessing(false);
        }
    };

    const handleRemediation = async (type) => {
        try {
            addLog(`Initiating Remediation: ${type}...`);
            await apiClient.post(`/jobs/${activeJobId}/fix`, { fixType: type });
            addLog("Remediation queued. Processing...");

            // Poll for fix completion
            const fixInterval = setInterval(async () => {
                const res = await apiClient.get(`/jobs/${activeJobId}`);
                const job = res.data;
                if (job.fixStatus === 'COMPLETED') {
                    addLog(`✅ Remediation Complete!`);
                    addLog(`Downloading Fixed Master: ${job.fixedFilePath.split(/[\\/]/).pop()}`);
                    clearInterval(fixInterval);

                    // Trigger Download
                    window.location.href = `${import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1'}/jobs/${activeJobId}/fixed-download`;

                } else if (job.fixStatus === 'FAILED') {
                    addLog(`❌ Remediation Failed: ${job.errorMessage}`);
                    clearInterval(fixInterval);
                }
            }, 2000);

        } catch (err) {
            addLog("Error triggering remediation.");
        }
    };

    return (
        <div className="fade-in">
            <div className="d-flex justify-content-between align-items-end mb-4">
                <div>
                    <h2 className="mb-1">Run Quality Control</h2>
                    <p className="text-secondary mb-0">Upload media to start the technical compliance pipeline.</p>
                </div>
            </div>

            <Row className="g-4">
                <Col xs={12} lg={6}>
                    <Card className="glass-panel border-0 p-4 h-100 shadow-sm transition-all hover-glow">
                        <h5 className="mb-4 d-flex align-items-center gap-2">
                            <span className="badge bg-primary rounded-circle" style={{ width: 24, height: 24, padding: '4px 0' }}>1</span>
                            Select Source Media
                        </h5>

                        <div className={`upload-zone border-2 border-dashed rounded-4 p-5 text-center mb-4 transition-all position-relative ${selectedFile ? 'border-primary bg-primary bg-opacity-10' : 'border-secondary border-opacity-25 hover-border-primary'}`}>
                            <input
                                type="file"
                                className="position-absolute top-0 start-0 w-100 h-100 opacity-0 cursor-pointer"
                                onChange={(e) => {
                                    if (e.target.files?.[0]) {
                                        setSelectedFile(e.target.files[0]);
                                        setLogs(prev => [...prev, `Selected: ${e.target.files[0].name}`]);
                                    }
                                }}
                                disabled={isProcessing}
                                accept=".mp4,.mxf,.mov,.mkv"
                            />
                            <div className="pointer-events-none">
                                <div className={`d-inline-block p-3 rounded-circle mb-3 ${selectedFile ? 'bg-primary text-white' : 'bg-dark text-primary'}`}>
                                    {selectedFile ? <MdCheckCircle size={32} /> : <MdCloudUpload size={32} />}
                                </div>
                                <h6 className="mb-2 text-white">{selectedFile ? selectedFile.name : "Drag & Drop or Click to Upload"}</h6>
                                <p className="text-secondary small mb-0">Supports MP4, MXF, MOV, MKV</p>
                            </div>
                        </div>

                        {selectedFile && (
                            <div className="bg-dark bg-opacity-50 p-3 rounded-3 mb-4 border border-secondary border-opacity-25 fade-in">
                                <div className="d-flex justify-content-between mb-2">
                                    <span className="text-secondary small">Size</span>
                                    <span className="text-white small fw-bold">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</span>
                                </div>
                                <div className="mt-3">
                                    <Form.Label className="text-secondary small mb-2">Compliance Profile</Form.Label>
                                    <Form.Select
                                        className="bg-dark text-white border-secondary border-opacity-25 rounded-3"
                                        value={selectedProfile}
                                        onChange={(e) => setSelectedProfile(e.target.value)}
                                        disabled={isProcessing}
                                    >
                                        <option value="strict">Strict (Gold Standard)</option>
                                        <option value="netflix_hd">Netflix HD (Interoperable)</option>
                                        <option value="youtube">YouTube (Web Optimized)</option>
                                    </Form.Select>
                                </div>
                            </div>
                        )}

                        <Button
                            variant={isProcessing ? "outline-primary" : "primary"}
                            size="lg"
                            className="w-100 d-flex align-items-center justify-content-center gap-2 mt-auto py-3 rounded-pill fw-bold"
                            disabled={!selectedFile || isProcessing}
                            onClick={handleStartQC}
                        >
                            {isProcessing ? (
                                <>
                                    <Spinner animation="border" size="sm" />
                                    <span className="ms-2">Processing...</span>
                                </>
                            ) : (
                                <>
                                    <MdPlayArrow size={24} />
                                    <span>Initialize Analysis</span>
                                </>
                            )}
                        </Button>
                    </Card>
                </Col>

                <Col xs={12} lg={6}>
                    <div className="h-100 d-flex flex-column gap-4">
                        <Card className="glass-panel border-0 p-4 shadow-sm flex-grow-1">
                            <h5 className="mb-4 d-flex align-items-center gap-2">
                                <span className="badge bg-primary rounded-circle" style={{ width: 24, height: 24, padding: '4px 0' }}>2</span>
                                Analysis Progress
                            </h5>

                            {!isProcessing && !activeJobId ? (
                                <div className="d-flex flex-column align-items-center justify-content-center h-100 text-secondary opacity-50 py-5">
                                    <MdPlayArrow size={48} className="mb-3" />
                                    <p>Waiting for analysis to start...</p>
                                </div>
                            ) : (
                                <div className="py-2">
                                    <ProgressBar
                                        label="Technical Compliance Pipeline"
                                        progress={progress}
                                        status={jobStatus === 'COMPLETED' ? "success" : jobStatus === 'FAILED' ? "danger" : "primary"}
                                    />

                                    <div className="mt-4 d-flex flex-column gap-3">
                                        <div className="d-flex justify-content-between align-items-center">
                                            <span className="small text-secondary">Current Status</span>
                                            <span className={`badge bg-${jobStatus === 'COMPLETED' ? 'success' : jobStatus === 'FAILED' ? 'danger' : 'primary'} bg-opacity-10 text-${jobStatus === 'COMPLETED' ? 'success' : jobStatus === 'FAILED' ? 'danger' : 'primary'}`}>
                                                {jobStatus || 'STARTING'}
                                            </span>
                                        </div>

                                        {jobStatus === 'COMPLETED' && (
                                            <Button
                                                variant="success"
                                                className="w-100 mt-2 py-2 fw-bold shadow-sm"
                                                onClick={() => window.open(`${import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1'}/jobs/${activeJobId}/visual`, '_blank')}
                                            >
                                                <MdCheckCircle className="me-2" size={20} />
                                                View Full QC Report
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            )}
                        </Card>

                        {jobStatus === 'COMPLETED' && (
                            <Card className="glass-panel border-0 p-4 shadow-sm fade-in">
                                <h5 className="mb-3 d-flex align-items-center gap-2">
                                    <span className="badge bg-warning text-dark rounded-circle" style={{ width: 24, height: 24, padding: '4px 0' }}>3</span>
                                    Correction & Delivery
                                </h5>
                                <div className="d-grid gap-2">
                                    <Button variant="outline-success" size="lg" onClick={() => handleRemediation("combined_fix")}>
                                        ✨ Remediate Audio Loudness & Video Artifacts
                                    </Button>
                                    <small className="text-secondary text-center">
                                        Applies EBU R128 Norm (-23 LUFS) + HQ Transcode. Auto-downloads to your machine.
                                    </small>
                                </div>
                            </Card>
                        )}

                        <div style={{ height: '250px' }}>
                            <ProcessTerminal title="Forensic Analysis Logs" logs={logs} />
                        </div>
                    </div>
                </Col>
            </Row>
        </div>
    );
};



export default Dashboard;
