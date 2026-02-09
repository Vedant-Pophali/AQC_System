import React from 'react';
import { AppBar, Toolbar, Typography, Box, Badge, Container } from '@mui/material';
import { BroadcastOnPersonal, Circle } from '@mui/icons-material';

interface NavigationProps {
    systemStatus?: 'online' | 'busy' | 'offline';
}

const Navigation: React.FC<NavigationProps> = ({ systemStatus = 'online' }) => {
    const getStatusColor = () => {
        switch (systemStatus) {
            case 'online': return 'success.main';
            case 'busy': return 'warning.main';
            case 'offline': return 'error.main';
            default: return 'text.secondary';
        }
    };

    return (
        <AppBar position="sticky" sx={{ bgcolor: 'background.paper', mb: 4, backgroundImage: 'none', boxShadow: 1 }}>
            <Container maxWidth="xl">
                <Toolbar disableGutters>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1 }}>
                        <BroadcastOnPersonal color="primary" sx={{ fontSize: 30 }} />
                        <Typography variant="h6" color="text.primary" fontWeight="bold" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                            AQC System
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ borderLeft: 1, borderColor: 'divider', pl: 1, ml: 1 }}>
                            v2.0
                        </Typography>
                    </Box>

                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 0.5, borderRadius: 5, bgcolor: 'action.hover', border: 1, borderColor: 'divider' }}>
                        <Circle sx={{ color: getStatusColor(), fontSize: 12 }} />
                        <Typography variant="caption" fontWeight="bold" color="text.secondary" sx={{ textTransform: 'uppercase' }}>
                            System {systemStatus}
                        </Typography>
                    </Box>
                </Toolbar>
            </Container>
        </AppBar>
    );
};

export default Navigation;
