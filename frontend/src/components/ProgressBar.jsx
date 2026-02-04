import React from 'react';
import { ProgressBar as BsProgressBar } from 'react-bootstrap';

const ProgressBar = ({ progress = 0, status = 'primary', label }) => {
    return (
        <div className="w-100">
            {label && (
                <div className="d-flex justify-content-between mb-2 small text-uppercase fw-bold text-secondary">
                    <span>{label}</span>
                    <span>{progress}%</span>
                </div>
            )}
            <BsProgressBar
                now={progress}
                variant={status}
                animated={progress < 100 && progress > 0}
                striped
                className="progress-sm bg-dark border border-secondary border-opacity-25"
                style={{ height: '8px', borderRadius: '4px' }}
            />
        </div>
    );
};

export default ProgressBar;
