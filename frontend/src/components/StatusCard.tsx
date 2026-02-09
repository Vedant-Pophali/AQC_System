import React from 'react';
import { Card, Box, Typography, SvgIconTypeMap } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';
import { OverridableComponent } from '@mui/material/OverridableComponent';

interface StatusCardProps {
    label: string;
    value: string;
    trend?: number;
    status?: string;
    icon?: OverridableComponent<SvgIconTypeMap<{}, "svg">> & { muiName: string }; // Type for MUI Icon
}

const StatusCard: React.FC<StatusCardProps> = ({ label, value, trend, status = 'primary', icon: Icon }) => {
    const getStatusColor = () => {
        switch (status) {
            case 'success': return 'success.main';
            case 'warning': return 'warning.main';
            case 'danger': return 'error.main';
            case 'info': return 'info.main';
            default: return 'primary.main';
        }
    };

    const color = getStatusColor();
    const isPositive = trend && trend > 0;

    return (
        <Card sx={{ height: '100%', position: 'relative', overflow: 'hidden', p: 3, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <Box sx={{ position: 'absolute', top: 16, right: 16, opacity: 0.1 }}>
                {Icon && <Icon sx={{ fontSize: 64, color: color }} />}
            </Box>

            <Box sx={{ position: 'relative', zIndex: 1 }}>
                <Typography variant="caption" color="text.secondary" fontWeight="bold" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                    {label}
                </Typography>
                <Typography variant="h4" fontWeight="bold" sx={{ mt: 1, color: 'text.primary' }}>
                    {value}
                </Typography>
            </Box>

            {trend !== undefined && (
                <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1, color: isPositive ? 'success.main' : 'error.main' }}>
                    {isPositive ? <TrendingUp fontSize="small" /> : <TrendingDown fontSize="small" />}
                    <Typography variant="body2" fontWeight="bold">
                        {Math.abs(trend)}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        vs last week
                    </Typography>
                </Box>
            )}

            <Box
                sx={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    width: '100%',
                    height: 4,
                    background: `linear-gradient(90deg, ${color}, transparent)`
                }}
            />
        </Card>
    );
};

export default StatusCard;
