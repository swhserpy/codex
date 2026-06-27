import { useEffect, useState } from 'react';
import Layout from '../components/Layout';

interface SystemStats {
  cpu_percent: number; cpu_count: number;
  memory_total: number; memory_used: number; memory_percent: number;
  disk_total: number; disk_used: number; disk_percent: number;
  uptime_seconds: number; hostname: string; platform: string;
  load_1m: number; load_5m: number; load_15m: number;
}

function fmtBytes(b: number): string {
  if (!b) return '0 B';
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let v = b;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(1)} ${u[i]}`;
}

function fmtUptime(s: number): string {
  const d = Math.floor(s / 86400); s %= 86400;
  const h = Math.floor(s / 3600); s %= 3600;
  const m = Math.floor(s / 60);
  return `${d}d ${h}h ${m}m`;
}

function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color || 'text-gray-100'}`}>{value}</div>
      {sub && <div className="text-xs text-gray-600 mt-1">{sub}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [err, setErr] = useState('');

  const fetchStats = async () => {
    const token = localStorage.getItem('token');
    try {
      const res = await fetch('/api/system', { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setStats(await res.json());
      setErr('');
    } catch (e: any) { setErr(e.message); }
  };

  useEffect(() => { fetchStats(); const t = setInterval(fetchStats, 10000); return () => clearInterval(t); }, []);

  if (!stats) {
    return <Layout><div className="flex items-center justify-center h-64 text-gray-500">Loading...</div></Layout>;
  }

  const memPct = stats.memory_percent;
  const diskPct = stats.disk_percent;
  const cpuPct = stats.cpu_percent;

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold">Dashboard</h2>
          <p className="text-sm text-gray-500">{stats.hostname} · {stats.platform}</p>
        </div>
        <button onClick={fetchStats} className="text-xs text-gray-500 hover:text-gray-300 bg-gray-800 px-3 py-1.5 rounded-lg transition-colors">↻ Refresh</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="CPU" value={`${cpuPct}%`} sub={`${stats.cpu_count} cores`} color={cpuPct > 80 ? 'text-red-400' : cpuPct > 50 ? 'text-yellow-400' : 'text-green-400'} />
        <StatCard label="Memory" value={`${memPct}%`} sub={`${fmtBytes(stats.memory_used)} / ${fmtBytes(stats.memory_total)}`} color={memPct > 80 ? 'text-red-400' : memPct > 50 ? 'text-yellow-400' : 'text-green-400'} />
        <StatCard label="Disk" value={`${diskPct}%`} sub={`${fmtBytes(stats.disk_used)} / ${fmtBytes(stats.disk_total)}`} color={diskPct > 80 ? 'text-red-400' : diskPct > 50 ? 'text-yellow-400' : 'text-green-400'} />
        <StatCard label="Uptime" value={fmtUptime(stats.uptime_seconds)} sub={`Load: ${stats.load_1m} / ${stats.load_5m} / ${stats.load_15m}`} />
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">Resource Usage</h3>
        <div className="space-y-4">
          {[
            { label: 'CPU', pct: cpuPct, color: cpuPct > 80 ? 'bg-red-500' : cpuPct > 50 ? 'bg-yellow-500' : 'bg-green-500' },
            { label: 'Memory', pct: memPct, color: memPct > 80 ? 'bg-red-500' : memPct > 50 ? 'bg-yellow-500' : 'bg-blue-500' },
            { label: 'Disk', pct: diskPct, color: diskPct > 80 ? 'bg-red-500' : diskPct > 50 ? 'bg-yellow-500' : 'bg-blue-500' },
          ].map(({ label, pct, color }) => (
            <div key={label}>
              <div className="flex justify-between text-xs text-gray-400 mb-1"><span>{label}</span><span>{pct}%</span></div>
              <div className="bg-gray-800 rounded-full h-2 overflow-hidden">
                <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {err && <div className="mt-4 text-sm text-red-400">Error: {err}</div>}
    </Layout>
  );
}
