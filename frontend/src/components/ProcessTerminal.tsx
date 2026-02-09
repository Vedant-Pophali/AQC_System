import React, { useEffect, useRef } from 'react';
import { Card } from 'react-bootstrap'; // Keeping bootstrap for now or switching to MUI? 
// Plan said "Adopt Material UI". I should switch this to MUI Box/Card/Typography.
import { Box, Typography, Paper } from '@mui/material';

interface ProcessTerminalProps {
    title: string;
    logs: string[];
}

const ProcessTerminal: React.FC<ProcessTerminalProps> = ({ title, logs }) => {
    const terminalRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <Paper
            sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                bgcolor: '#1e1e1e',
                color: '#00ff00',
                fontFamily: 'monospace',
                overflow: 'hidden',
                borderRadius: 2,
                border: '1px solid #333'
            }}
        >
            <Box sx={{ p: 1, borderBottom: '1px solid #333', bgcolor: '#252526' }}>
                <Typography variant="caption" sx={{ color: '#ccc' }}>{title}</Typography>
            </Box>
            <Box
                ref={terminalRef}
                sx={{
                    flexGrow: 1,
                    overflowY: 'auto',
                    p: 2,
                    '&::-webkit-scrollbar': { width: '8px' },
                    '&::-webkit-scrollbar-thumb': { bgcolor: '#444', borderRadius: '4px' }
                }}
            >
                {logs.length === 0 ? (
                    <Typography variant="body2" sx={{ opacity: 0.5 }}>Waiting for logs...</Typography>
                ) : (
                    logs.map((log, index) => (
                        <div key={index} className="log-entry">
                            <span style={{ color: '#569cd6' }}>➜</span> {log}
                        </div>
                    ))
                )}
            </Box>
        </Paper>
    );
};

export default ProcessTerminal;
