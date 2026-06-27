import { useEffect, useState } from 'react';
import Layout from '../components/Layout';

interface TaskInfo { path: string; exists: boolean; executable: boolean; }
interface TaskResult { task: string; stdout: string; stderr: string; return_code: number; success: boolean; }

export default function TasksPage() {
  const [tasks, setTasks] = useState<Record<string, TaskInfo>>({});
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [error, setError] = useState('');

  const fetchTasks = async () => {
    const token = localStorage.getItem('token');
    try {
      const res = await fetch('/api/tasks', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setTasks(data.tasks || {});
    } catch (e: any) { setError(e.message); }
  };

  useEffect(() => { fetchTasks(); }, []);

  const runTask = async (key: string) => {
    setRunning(key); setResult(null); setError('');
    const token = localStorage.getItem('token');
    try {
      const res = await fetch('/api/tasks/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ task_key: key }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    finally { setRunning(null); }
  };

  const label = (k: string) => ({ backup: '📦 Backup', cleanup: '🧹 Cleanup', restart_dashboard: '♻ Restart Dashboard' }[k] || k);

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Tasks</h2>
        <button onClick={fetchTasks} className="text-xs text-gray-500 hover:text-gray-300 bg-gray-800 px-3 py-1.5 rounded-lg">↻ Refresh</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {Object.entries(tasks).map(([key, info]) => (
          <div key={key} className={`bg-gray-900 border rounded-xl p-5 ${info.exists ? 'border-gray-800' : 'border-gray-800/50 opacity-50'}`}>
            <div className="text-sm font-semibold mb-1">{label(key)}</div>
            <div className="text-xs text-gray-500 mb-3 font-mono">{info.path}</div>
            <div className="flex items-center gap-2 mb-4">
              <span className={`text-xs px-2 py-0.5 rounded ${info.exists ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                {info.exists ? 'Found' : 'Missing'}
              </span>
              {info.exists && <span className={`text-xs px-2 py-0.5 rounded ${info.executable ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'}`}>{info.executable ? 'Executable' : 'Not executable'}</span>}
            </div>
            <button
              onClick={() => runTask(key)}
              disabled={running === key || !info.exists}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-30 text-white text-sm px-4 py-2 rounded-lg transition-colors"
            >
              {running === key ? 'Running...' : '▶ Run'}
            </button>
          </div>
        ))}
        {!Object.keys(tasks).length && !error && <div className="col-span-full text-center text-gray-600 py-10">No tasks configured.</div>}
      </div>

      {error && <div className="bg-red-900/20 border border-red-800/50 rounded-xl p-4 text-sm text-red-400 mb-4">{error}</div>}

      {result && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-sm font-semibold">Result: {label(result.task)}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${result.success ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
              {result.success ? 'Success' : `Failed (${result.return_code})`}
            </span>
          </div>
          {result.stdout && (
            <div className="mb-2">
              <div className="text-xs text-gray-500 mb-1">stdout:</div>
              <pre className="bg-gray-950 rounded-lg p-3 text-xs text-gray-300 font-mono overflow-auto max-h-40">{result.stdout}</pre>
            </div>
          )}
          {result.stderr && (
            <div>
              <div className="text-xs text-gray-500 mb-1">stderr:</div>
              <pre className="bg-gray-950 rounded-lg p-3 text-xs text-red-300 font-mono overflow-auto max-h-40">{result.stderr}</pre>
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
