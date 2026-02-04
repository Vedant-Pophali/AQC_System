import React from 'react';
import { Card, Button } from 'react-bootstrap';
import { MdDownload, MdVisibility } from 'react-icons/md';

const Reports = () => {
    return (
        <div className="fade-in">
            <div className="d-flex justify-content-between align-items-end mb-4">
                <div>
                    <h2 className="mb-1">Quality Reports</h2>
                    <p className="text-secondary mb-0">Archive of compliance certificates and failure logs.</p>
                </div>
            </div>

            <Card className="glass-panel border-0">
                <div className="table-responsive">
                    <table className="table table-dark table-hover mb-0 align-middle">
                        <thead>
                            <tr className="border-bottom border-secondary border-opacity-25">
                                <th className="py-3 ps-4 text-secondary text-uppercase small">Job ID</th>
                                <th className="py-3 text-secondary text-uppercase small">File Name</th>
                                <th className="py-3 text-secondary text-uppercase small">Date</th>
                                <th className="py-3 text-secondary text-uppercase small">Status</th>
                                <th className="py-3 pe-4 text-end text-secondary text-uppercase small">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {[1024, 1023, 1022, 1021, 1020].map((id, idx) => (
                                <tr key={id}>
                                    <td className="ps-4 text-monospace text-secondary small">#{id}</td>
                                    <td className="fw-medium">EPisdoe_Final_Cut_v{idx + 1}.mov</td>
                                    <td className="text-secondary small">Oct {24 - idx}, 2025</td>
                                    <td>
                                        {idx === 2 ? (
                                            <span className="badge bg-danger bg-opacity-25 text-danger border border-danger border-opacity-25">FAILED</span>
                                        ) : (
                                            <span className="badge bg-success bg-opacity-25 text-success border border-success border-opacity-25">COMPLIANT</span>
                                        )}
                                    </td>
                                    <td className="pe-4 text-end">
                                        <Button variant="link" className="text-decoration-none text-light p-0 me-3" title="View Report">
                                            <MdVisibility size={18} />
                                        </Button>
                                        <Button variant="link" className="text-decoration-none text-secondary p-0" title="Download JSON">
                                            <MdDownload size={18} />
                                        </Button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </Card>
        </div>
    );
};

export default Reports;
