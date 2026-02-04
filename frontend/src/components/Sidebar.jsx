import React from 'react';
import { Nav } from 'react-bootstrap';
import { NavLink } from 'react-router-dom';
import {
    MdDashboard,
    MdQueuePlayNext,
    MdHistory,
    MdSettings
} from 'react-icons/md';

const Sidebar = () => {
    return (
        <div className="h-100 d-flex flex-column p-3 glass-panel rounded-3">
            <h6 className="text-uppercase text-muted fw-bold mb-4 ps-2" style={{ fontSize: '0.75rem', letterSpacing: '1px' }}>Menu</h6>
            <Nav className="flex-column gap-2 flex-grow-1">
                <NavLink
                    to="/"
                    className={({ isActive }) =>
                        `nav-link d-flex align-items-center gap-3 px-3 py-2 rounded-2 transition-all ${isActive ? 'bg-primary text-white shadow-sm' : 'text-secondary hover-light-bg'
                        }`
                    }
                >
                    <MdDashboard size={20} />
                    <span>Overview</span>
                </NavLink>

                <NavLink
                    to="/dashboard"
                    className={({ isActive }) =>
                        `nav-link d-flex align-items-center gap-3 px-3 py-2 rounded-2 transition-all ${isActive ? 'bg-primary text-white shadow-sm' : 'text-secondary hover-light-bg'
                        }`
                    }
                >
                    <MdQueuePlayNext size={20} />
                    <span>Run QC</span>
                </NavLink>

                <NavLink
                    to="/reports"
                    className={({ isActive }) =>
                        `nav-link d-flex align-items-center gap-3 px-3 py-2 rounded-2 transition-all ${isActive ? 'bg-primary text-white shadow-sm' : 'text-secondary hover-light-bg'
                        }`
                    }
                >
                    <MdHistory size={20} />
                    <span>Reports</span>
                </NavLink>
            </Nav>

            <div className="mt-auto pt-4 border-top border-secondary border-opacity-25">
                <NavLink
                    to="/settings"
                    className={({ isActive }) =>
                        `nav-link d-flex align-items-center gap-3 px-3 py-2 rounded-2 transition-all ${isActive ? 'bg-secondary text-white shadow-sm' : 'text-secondary hover-light-bg'
                        }`
                    }
                >
                    <MdSettings size={20} />
                    <span>Settings</span>
                </NavLink>
            </div>
        </div>
    );
};

export default Sidebar;
