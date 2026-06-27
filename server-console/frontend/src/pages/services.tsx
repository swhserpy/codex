import { useEffect, useState } from 'react';
import Layout from '../components/Layout';

interface Container { ID: string; Image: string; Names: string; State: string; Status: string; Ports: string; CreatedAt: string; }

export default function ServicesPage() {
  const [containers, setContainers] = useState<Container[]>([]);
  const [error, setError] = useState('');

  const fetchSvcs = async () => {
    const token = localStorage.getItem('token');
    try {
      const res = await fetch('/api/services', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setContainers(data.containers || []);
      setError(data.error || '');
    } catch (e: any) { setError(e.message); }
  };

  useEffect(() => { fetchSvcs(); const t = setInterval(fetchSvcs, 15000); return () => clearInterval(t); }, []);

  const stateColor = (s: string) => s === 'running' ? 'text-green-400' : s === 'exited' || s === 'dead' ? 'text-red-400' : 'text-yellow-400';

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Services</h2>
        <button onClick={fetchSvcs} className="text-xs text-gray-500 hover:text-gray-300 bg-gray-800 px-3 py-1.5 rounded-lg">↻ Refresh</button>
      </div>

      {error && error !== 'Docker not installed' && <div className="text-red-400 text-sm mb-4">Error: {error}</div>}

      {!containers.length ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center text-gray-500">
          {error === 'Docker not installed' ? '🐳 Docker is not installed on this server.' : 'No containers found.'}
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                <th className="text-left p-3 font-medium">Name</th>
                <th className="text-left p-3 font-medium">Image</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-left p-3 font-medium">State</th>
                <th className="text-left p-3 font-medium">Ports</th>
                <th className="text-left p-3 font-medium">ID</th>
              </tr>
            </thead>
            <tbody>
              {containers.map((c) => (
                <tr key={c.ID} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="p-3 font-medium">{c.Names}</td>
                  <td className="p-3 text-gray-400">{c.Image}</td>
                  <td className="p-3 text-gray-400 text-xs">{c.Status}</td>
                  <td className="p-3"><span className={`${stateColor(c.State)} font-medium`}>{c.State}</span></td>
                  <td className="p-3 text-gray-400 text-xs">{c.Ports || '-'}</td>
                  <td className="p-3 text-gray-500 text-xs font-mono">{c.ID.substring(0, 12)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
