import React, { useState, useEffect } from 'react';
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Area, AreaChart,
} from 'recharts';
import { getTrend } from '../api';

/**
 * TrendChart -- Repo Health Over Time
 * Line chart showing average entropy score over the last 12 months.
 * Design: flat teal stroke, no gradient fill, sharp grid lines.
 */

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#111111',
      border: '1px solid #2A2A2A',
      borderRadius: 2,
      padding: '8px 12px',
      fontSize: '0.78rem',
      fontFamily: 'var(--font-mono)',
    }}>
      <div style={{ color: '#666666', marginBottom: 4, fontFamily: 'var(--font-sans)' }}>{label}</div>
      <div style={{ color: '#0D9488', fontWeight: 600 }}>
        avg entropy: {payload[0]?.value?.toFixed(1)}
      </div>
      {payload[0]?.payload?.module_count && (
        <div style={{ color: '#AAAAAA', fontSize: '0.72rem', marginTop: 2 }}>
          {payload[0].payload.module_count} modules
        </div>
      )}
    </div>
  );
};

export default function TrendChart({ repoId }) {
  const [data, setData]       = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!repoId) return;
    setLoading(true);
    getTrend(repoId, 365)
      .then(d => setData(d))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [repoId]);

  if (loading) {
    return (
      <div className="loading-container" style={{ minHeight: 200 }}>
        <div className="spinner" />
        <div className="loading-text">Loading trend data...</div>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="empty-state" style={{ minHeight: 200 }}>
        <div className="empty-state-text" style={{ color: 'var(--dash-text-3)' }}>
          Not enough historical data yet. Run multiple scans over time to see trends.
        </div>
      </div>
    );
  }

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1F1F1F"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{ fill: '#666666', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            axisLine={{ stroke: '#2A2A2A' }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: '#666666', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            axisLine={{ stroke: '#2A2A2A' }}
            tickLine={false}
            width={35}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="avg_entropy"
            stroke="#0D9488"
            strokeWidth={2}
            fill="#0D9488"
            fillOpacity={0.06}
            dot={false}
            activeDot={{ r: 3, fill: '#0D9488', stroke: '#0A0A0A', strokeWidth: 2 }}
            name="avg entropy"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
