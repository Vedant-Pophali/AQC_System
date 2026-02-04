import React from 'react';
import { Card } from 'react-bootstrap';

const ProcessTerminal = ({ logs = [], title = "System Logs" }) => {
    return (
        <Card className="bg-black border border-secondary border-opacity-25 h-100 shadow-lg">
            <Card.Header className="bg-dark bg-opacity-50 border-bottom border-secondary border-opacity-25 py-2 px-3 d-flex align-items-center gap-2">
                <div className="d-flex gap-2">
                    <div className="rounded-circle bg-danger" style={{ width: 8, height: 8 }}></div>
                    <div className="rounded-circle bg-warning" style={{ width: 8, height: 8 }}></div>
                    <div className="rounded-circle bg-success" style={{ width: 8, height: 8 }}></div>
                </div>
                <span className="ms-3 text-monospace text-secondary small">{title}</span>
            </Card.Header>
            <Card.Body className="p-3 overflow-auto custom-scrollbar" style={{ maxHeight: '300px', minHeight: '200px', fontFamily: '"JetBrains Mono", "Courier New", monospace' }}>
                {logs.length === 0 ? (
                    <div className="text-muted fst-italic opacity-50">Waiting for process output...</div>
                ) : (
                    logs.map((log, index) => (
                        <div key={index} className="text-success small mb-1">
                            <span className="opacity-50 me-2">[{new Date().toLocaleTimeString()}]</span>
                            {log}
                        </div>
                    ))
                )}
                {/* Typing cursor animation */}
                <div className="text-secondary small mt-2 blink-cursor">_</div>
            </Card.Body>
        </Card>
    );
};

export default ProcessTerminal;
