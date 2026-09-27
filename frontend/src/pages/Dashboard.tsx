import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Users, Video, Activity, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';

const data = [
  { time: '09:00', attention: 85 },
  { time: '09:15', attention: 88 },
  { time: '09:30', attention: 92 },
  { time: '09:45', attention: 80 },
  { time: '10:00', attention: 75 },
  { time: '10:15', attention: 82 },
  { time: '10:30', attention: 90 },
];

const StatCard = ({ title, value, trend, trendValue, icon, delay }) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="glass-panel glass-panel-interactive stat-card col-span-3"
  >
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div>
        <div className="stat-title">{title}</div>
        <div className="stat-value">{value}</div>
      </div>
      <div style={{ padding: '0.75rem', background: 'var(--bg-tertiary)', borderRadius: '12px' }}>
        {icon}
      </div>
    </div>
    <div className={`stat-trend ${trend === 'up' ? 'positive' : 'negative'}`}>
      {trend === 'up' ? '↑' : '↓'} {trendValue} vs last week
    </div>
  </motion.div>
);

const Dashboard = () => {
  const [stats, setStats] = React.useState<any>(null);

  React.useEffect(() => {
    fetch('http://localhost:8000/api/v1/analytics/system/dashboard')
      .then(res => res.json())
      .then(d => setStats(d))
      .catch(err => console.error(err));
  }, []);

  const avgAttention = stats?.avg_attention_rate || 0;
  const activeSessionsCount = stats?.active_sessions_count || 0;
  const totalStudents = stats?.total_students || 0;
  const attentionDrops = stats?.attention_drops_today || 0;
  
  const liveSessions = stats?.active_sessions?.length > 0 ? stats.active_sessions : [
    { name: 'No Active Sessions', students: 0, attention: 0 }
  ];

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1 className="text-gradient" style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Overview</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Real-time insights across all your active classes.</p>
      </header>

      <div className="dashboard-grid">
        <StatCard 
          title="Avg. Attention Rate" 
          value={`${avgAttention}%`} 
          trend="up" 
          trendValue="0%" 
          icon={<Activity size={24} color="var(--accent-secondary)" />} 
          delay={0.1}
        />
        <StatCard 
          title="Active Sessions" 
          value={activeSessionsCount.toString()} 
          trend="up" 
          trendValue="0" 
          icon={<Video size={24} color="var(--success)" />} 
          delay={0.2}
        />
        <StatCard 
          title="Total Students" 
          value={totalStudents.toString()} 
          trend="up" 
          trendValue="0" 
          icon={<Users size={24} color="var(--accent-primary)" />} 
          delay={0.3}
        />
        <StatCard 
          title="Attention Drops" 
          value={attentionDrops.toString()} 
          trend="down" 
          trendValue="0" 
          icon={<AlertTriangle size={24} color="var(--warning)" />} 
          delay={0.4}
        />

        {/* Chart Section */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass-panel col-span-8" 
          style={{ padding: '1.5rem', minHeight: 400 }}
        >
          <h2 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>Attention Trends Today</h2>
          <div style={{ height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorAttention" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-primary)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--accent-primary)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" vertical={false} />
                <XAxis dataKey="time" stroke="var(--text-tertiary)" tick={{fill: 'var(--text-tertiary)'}} axisLine={false} tickLine={false} />
                <YAxis stroke="var(--text-tertiary)" tick={{fill: 'var(--text-tertiary)'}} axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-light)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <Area type="monotone" dataKey="attention" stroke="var(--accent-primary)" strokeWidth={3} fillOpacity={1} fill="url(#colorAttention)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Live Sessions Feed */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-panel col-span-4" 
          style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}
        >
          <h2 style={{ marginBottom: '1.5rem', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span className="status-dot active pulse-glow" style={{ animation: 'pulse-glow 2s infinite' }}></span>
            Live Sessions
          </h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {liveSessions.map((session: any, i: number) => (
              <div key={i} className="glass-panel-interactive" style={{ padding: '1rem', borderRadius: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-light)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <div style={{ fontWeight: 600 }}>{session.name || `Session ${session.id}`}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{session.students || 0} students</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{ flex: 1, height: 6, background: 'var(--bg-tertiary)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ 
                      width: `${session.attention || 0}%`, 
                      height: '100%', 
                      background: (session.attention || 0) > 80 ? 'var(--success)' : 'var(--warning)',
                      borderRadius: 3
                    }} />
                  </div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{session.attention || 0}%</div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

      </div>
    </div>
  );
};

export default Dashboard;
