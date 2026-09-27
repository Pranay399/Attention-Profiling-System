import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, Activity, Settings, Video } from 'lucide-react';

const Sidebar = () => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'Active Sessions', path: '/sessions', icon: <Video size={20} /> },
    { name: 'Classrooms', path: '/classrooms', icon: <Users size={20} /> },
    { name: 'Analytics', path: '/analytics', icon: <Activity size={20} /> },
    { name: 'Settings', path: '/settings', icon: <Settings size={20} /> },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div style={{
          width: 32, height: 32, borderRadius: 8, 
          background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 15px var(--accent-glow)'
        }}>
          <Activity size={18} color="white" />
        </div>
        <span className="text-gradient">Focus AI</span>
      </div>
      
      <nav style={{ flex: 1 }}>
        {navItems.map((item) => (
          <NavLink 
            key={item.path} 
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            {item.icon}
            {item.name}
          </NavLink>
        ))}
      </nav>

      <div style={{ marginTop: 'auto', paddingTop: '2rem', borderTop: '1px solid var(--border-light)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="avatar">TJ</div>
          <div>
            <div style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-primary)' }}>Teacher Jane</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>jane@school.edu</div>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
