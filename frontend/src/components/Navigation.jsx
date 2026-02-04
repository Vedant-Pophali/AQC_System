import React from 'react';
import { Navbar, Container, Badge } from 'react-bootstrap';
import { RiBroadcastFill } from 'react-icons/ri';
import { BsCircleFill } from 'react-icons/bs';

const Navigation = ({ systemStatus = 'online' }) => {
    const getStatusColor = () => {
        switch (systemStatus) {
            case 'online': return 'text-success';
            case 'busy': return 'text-warning';
            case 'offline': return 'text-danger';
            default: return 'text-secondary';
        }
    };

    return (
        <Navbar expand="lg" variant="dark" className="glass-panel sticky-top mb-4">
            <Container fluid>
                <Navbar.Brand href="/" className="d-flex align-items-center gap-2 fw-bold text-uppercase tracking-wider">
                    <RiBroadcastFill className="text-primary" size={24} />
                    <span className="text-white">AQC System</span>
                    <span className="text-muted fs-6 border-start ps-2 ms-2">v2.0</span>
                </Navbar.Brand>

                <div className="d-flex align-items-center gap-3">
                    <div className="d-flex align-items-center gap-2 px-3 py-1 rounded-pill bg-dark bg-opacity-25 border border-white border-opacity-10">
                        <BsCircleFill className={`${getStatusColor()} small-pulsate`} size={10} />
                        <span className="text-uppercase small fw-bold text-muted" style={{ fontSize: '0.75rem' }}>
                            System {systemStatus}
                        </span>
                    </div>
                </div>
            </Container>
        </Navbar>
    );
};

export default Navigation;
