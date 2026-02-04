import React, { useState } from 'react';
import { Row, Col, Card, Form, Button, Alert } from 'react-bootstrap';
import { MdCloudUpload, MdPlayArrow } from 'react-icons/md';
import ProgressBar from '../components/ProgressBar';

const Dashboard = () => {
    const [selectedFile, setSelectedFile] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [progress, setProgress] = useState(0);

    const handleFileSelect = (e) => {
        if (e.target.files && e.target.files[0]) {
            setSelectedFile(e.target.files[0]);
        }
    };

    const handleStartQC = () => {
        if (!selectedFile) return;
        setIsProcessing(true);
        // Simulate progress
        let p = 0;
        const interval = setInterval(() => {
            p += 5;
            setProgress(p);
            if (p >= 100) {
                clearInterval(interval);
                // setIsProcessing(false); // Keep it "complete" state for demo
            }
        }, 500);
    };

    return (
        <div className="fade-in">
            <div className="d-flex justify-content-between align-items-end mb-4">
                <div>
                    <h2 className="mb-1">Run Quality Control</h2>
                    <p className="text-secondary mb-0">Upload media or select from storage to begin analysis.</p>
                </div>
            </div>

            <Row className="g-4">
                <Col xs={12} lg={6}>
                    <Card className="glass-panel border-0 p-4 h-100">
                        <h5 className="mb-4">1. Select Source Media</h5>

                        <div className="upload-zone border-2 border-dashed border-secondary border-opacity-25 rounded-3 p-5 text-center mb-4 transition-all hover-border-primary cursor-pointer position-relative">
                            <input
                                type="file"
                                className="position-absolute top-0 start-0 w-100 h-100 opacity-0 cursor-pointer"
                                onChange={handleFileSelect}
                                accept=".mp4,.mxf,.mov,.mkv"
                            />
                            <div className="pointer-events-none">
                                <div className="bg-dark d-inline-block p-3 rounded-circle mb-3">
                                    <MdCloudUpload size={32} className="text-primary" />
                                </div>
                                <h6 className="mb-2">{selectedFile ? selectedFile.name : "Drag & Drop or Click to Upload"}</h6>
                                <p className="text-secondary small mb-0">Supports MP4, MXF, MOV, MKV (Max 50GB)</p>
                            </div>
                        </div>

                        {selectedFile && (
                            <div className="bg-dark bg-opacity-50 p-3 rounded mb-4 border border-secondary border-opacity-25">
                                <div className="d-flex justify-content-between mb-2">
                                    <span className="text-secondary small">Selected File</span>
                                    <span className="text-white small fw-bold">{selectedFile.name}</span>
                                </div>
                                <div className="d-flex justify-content-between">
                                    <span className="text-secondary small">Size</span>
                                    <span className="text-white small fw-bold">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</span>
                                </div>
                            </div>
                        )}

                        <Button
                            variant="primary"
                            size="lg"
                            className="w-100 d-flex align-items-center justify-content-center gap-2 mt-auto"
                            disabled={!selectedFile || isProcessing}
                            onClick={handleStartQC}
                        >
                            <MdPlayArrow size={24} />
                            {isProcessing ? 'Processing Started...' : 'Initialize Analysis'}
                        </Button>
                    </Card>
                </Col>

                <Col xs={12} lg={6}>
                    <Card className="glass-panel border-0 p-4 h-100">
                        <h5 className="mb-4">2. Analysis Progress</h5>

                        {!isProcessing ? (
                            <div className="d-flex flex-column align-items-center justify-content-center h-75 text-secondary opacity-50">
                                <MdPlayArrow size={64} className="mb-3" />
                                <p>Waiting for job initialization...</p>
                            </div>
                        ) : (
                            <div className="py-4">
                                <Alert variant="info" className="bg-info bg-opacity-10 border-info border-opacity-25 text-info mb-4">
                                    <div className="d-flex gap-2">
                                        <div className="spinner-border spinner-border-sm" role="status"></div>
                                        <span>Analyzing video artifacts (BRISQUE Model)...</span>
                                    </div>
                                </Alert>

                                <ProgressBar
                                    label="Video Integrity Check"
                                    progress={progress}
                                    status={progress === 100 ? "success" : "primary"}
                                />

                                <div className="mt-4">
                                    <ProgressBar
                                        label="Audio Loudness (EBU R.128)"
                                        progress={Math.max(0, progress - 20)}
                                        status="info"
                                    />
                                </div>

                                <div className="mt-4">
                                    <ProgressBar
                                        label="Metadata Validation"
                                        progress={Math.max(0, progress - 10)}
                                        status="warning"
                                    />
                                </div>
                            </div>
                        )}
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default Dashboard;
