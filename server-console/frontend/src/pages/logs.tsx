import { useEffect, useState } from 'react';
import Layout from '../components/Layout';

const LOG_OPTIONS: Record<string, string> = {
  assistant: 'Assistant Server',
  dashboard: 'Dashboard',
  telegram_bot: 'Telegram Bot',
  system_auth: 'Auth Log',
  syslog: 'Syslog',
};

export default function LogsPage() {
  const [logKey, setLogKey] = useState('assistant');
  const [lines, setLines] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchLogs = async (key: string) => {
    setLoading(true); setError('');
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`/api/logs?log_key=${key}`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setLines(data.lines);
    } catch (e: any) { setError(e.message); setLines([]); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchLogs(logKey); }, [logKey]);

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Logs</h2>
        <button onClick={() => fetchLogs(logKey)} className="text-xs text-gray-500 hover:text-gray-300 bg-gray-800 px-3 py-1.5 rounded-lg">↻ Refresh</button>
      </div>

      <div className="mb-4">
        <select
          value={logKey}
          onChange={e => setLogKey(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
        >
          {Object.entries(LOG_OPTIONS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <span className="text-xs text-gray-600 ml-3">Last 100 lines</span>
        {loading && <span className="text-xs text-gray-500 ml-2">loading...</span>}
      </div>

      {error && <div className="text-red-400 text-sm mb-4">{error}</div>}

      <div className="bg-gray-950 border border-gray-800 rounded-xl overflow-hidden">
        <pre className="p-4 text-xs font-mono text-gray-300 overflow-auto max-h-[70vh] leading-relaxed">
          {lines.length > 0 ? lines.map((l, i) => <div key={i} className="hover:bg-gray-900/50 px-1">{l || ' '}</div>) : <span className="text-gray-600">(empty)</span>}
        </pre>
      </div>
    </Layout>
  );
}
