import React from 'react';
import { Card } from 'react-bootstrap';
import { BsArrowUpRight, BsArrowDownRight } from 'react-icons/bs';

const StatusCard = ({ label, value, trend, status = 'primary', icon: Icon }) => {
    const getStatusColor = () => {
        switch (status) {
            case 'success': return '#198754';
            case 'warning': return '#ffc107';
            case 'danger': return '#dc3545';
            case 'info': return '#0dcaf0';
            default: return '#0d6efd';
        }
    };

    const color = getStatusColor();

    return (
        <Card className="h-100 border-0 glass-panel hover-lift overflow-hidden">
            <div className="position-absolute top-0 end-0 p-3 opacity-10">
                {Icon && <Icon size={64} color={color} />}
            </div>

            <Card.Body className="position-relative z-1 d-flex flex-column justify-content-between">
                <div>
                    <h6 className="text-secondary text-uppercase fw-bold" style={{ fontSize: '0.75rem', letterSpacing: '1px' }}>
                        {label}
                    </h6>
                    <h2 className="display-6 fw-bold mb-0 text-white mt-2">
                        {value}
                    </h2>
                </div>

                {trend && (
                    <div className={`mt-3 d-flex align-items-center gap-2 small ${trend > 0 ? 'text-success' : 'text-danger'}`}>
                        {trend > 0 ? <BsArrowUpRight /> : <BsArrowDownRight />}
                        <span className="fw-semibold">
                            {Math.abs(trend)}%
                        </span>
                        <span className="text-secondary opacity-75">
                            vs last week
                        </span>
                    </div>
                )}
            </Card.Body>

            <div
                className="position-absolute bottom-0 start-0 w-100"
                style={{ height: '4px', background: `linear-gradient(90deg, ${color}, transparent)` }}
            />
        </Card>
    );
};

export default StatusCard;
