import React from 'react';
import { Box, Container, Grid, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import { Outlet } from 'react-router-dom';
import Navigation from './Navigation';
import Sidebar from './Sidebar';

// Dark Mode Theme inspired by "Google Blue, Google Grey" per requirements, 
// strictly creating a dark, premium feel.
const darkTheme = createTheme({
    palette: {
        mode: 'dark',
        primary: {
            main: '#4285F4', // Google Blue
        },
        background: {
            default: '#121212',
            paper: '#1E1E1E',
        },
        text: {
            primary: '#E8EAED',
            secondary: '#9AA0A6'
        }
    },
    typography: {
        fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
        button: {
            textTransform: 'none', // Modern feel
            fontWeight: 600
        }
    },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: 20 // Pill shape
                }
            }
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    backgroundImage: 'none',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
                }
            }
        }
    }
});

const Layout: React.FC = () => {
    return (
        <ThemeProvider theme={darkTheme}>
            <CssBaseline />
            <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: 'background.default' }}>
                <Navigation />

                <Container maxWidth="xl" sx={{ flexGrow: 1, px: { xs: 2, md: 4 }, pb: 4 }}>
                    <Grid container spacing={3} sx={{ height: '100%' }}>
                        <Grid item xs={12} md={3} lg={2} sx={{ display: { xs: 'none', md: 'block' } }}>
                            <Sidebar />
                        </Grid>

                        <Grid item xs={12} md={9} lg={10}>
                            <Box component="main" sx={{ height: '100%', overflowY: 'auto' }}>
                                <Outlet />
                            </Box>
                        </Grid>
                    </Grid>
                </Container>
            </Box>
        </ThemeProvider>
    );
};

export default Layout;
