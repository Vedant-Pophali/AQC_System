import React from 'react';
import { Box, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Typography } from '@mui/material';
import { NavLink, useLocation } from 'react-router-dom';
import {
    Dashboard,
    QueuePlayNext,
    History,
    Settings
} from '@mui/icons-material';

const Sidebar: React.FC = () => {
    const location = useLocation();

    const menuItems = [
        { text: 'Overview', icon: <Dashboard />, path: '/' },
        { text: 'Run QC', icon: <QueuePlayNext />, path: '/dashboard' },
        { text: 'Reports', icon: <History />, path: '/reports' },
    ];

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
            <Typography variant="overline" color="text.secondary" fontWeight="bold" sx={{ mb: 2, pl: 2 }}>
                Menu
            </Typography>

            <List component="nav" sx={{ flexGrow: 1 }}>
                {menuItems.map((item) => (
                    <ListItem key={item.text} disablePadding sx={{ mb: 1 }}>
                        <ListItemButton
                            component={NavLink}
                            to={item.path}
                            selected={location.pathname === item.path}
                            sx={{
                                borderRadius: 2,
                                '&.active': {
                                    bgcolor: 'primary.main',
                                    color: 'white',
                                    '& .MuiListItemIcon-root': { color: 'white' }
                                },
                                '&:hover': {
                                    bgcolor: 'action.hover'
                                }
                            }}
                        >
                            <ListItemIcon sx={{ minWidth: 40, color: location.pathname === item.path ? 'white' : 'text.secondary' }}>
                                {item.icon}
                            </ListItemIcon>
                            <ListItemText primary={item.text} primaryTypographyProps={{ fontSize: '0.9rem', fontWeight: 500 }} />
                        </ListItemButton>
                    </ListItem>
                ))}
            </List>

            <Box sx={{ pt: 2, borderTop: 1, borderColor: 'divider' }}>
                <List>
                    <ListItem disablePadding>
                        <ListItemButton
                            component={NavLink}
                            to="/settings"
                            selected={location.pathname === '/settings'}
                            sx={{
                                borderRadius: 2,
                                '&.active': { bgcolor: 'secondary.main', color: 'white' }
                            }}
                        >
                            <ListItemIcon sx={{ minWidth: 40 }}>
                                <Settings />
                            </ListItemIcon>
                            <ListItemText primary="Settings" />
                        </ListItemButton>
                    </ListItem>
                </List>
            </Box>
        </Box>
    );
};

export default Sidebar;
