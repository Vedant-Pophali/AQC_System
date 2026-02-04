import React from 'react';
import { Container, Row, Col } from 'react-bootstrap';
import { Outlet } from 'react-router-dom';
import Navigation from './Navigation';
import Sidebar from './Sidebar';

const Layout = () => {
    return (
        <div className="d-flex flex-column min-vh-100 bg-dark text-light overflow-hidden">
            <Navigation />

            <Container fluid className="flex-grow-1 px-4 pb-4">
                <Row className="h-100 g-4">
                    <Col xs={12} md={3} lg={2} className="h-100 d-none d-md-block" style={{ minHeight: '85vh' }}>
                        <Sidebar />
                    </Col>

                    <Col xs={12} md={9} lg={10} className="h-100 overflow-auto">
                        <main className="h-100 fade-in">
                            <Outlet />
                        </main>
                    </Col>
                </Row>
            </Container>
        </div>
    );
};

export default Layout;
