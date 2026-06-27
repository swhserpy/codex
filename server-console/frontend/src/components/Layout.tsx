import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

const NAV = [
  { path: '/dashboard', label: 'Dashboard', icon: '◉' },
  { path: '/services', label: 'Services', icon: '▣' },
  { path: '/logs', label: 'Logs', icon: '☰' },
  { path: '/tasks', label: 'Tasks', icon: '▶' },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem('token');
    if (!t) { router.replace('/'); return; }
    setToken(t);
  }, []);

  const logout = () => {
    localStorage.removeItem('token');
    router.replace('/');
  };

  if (!token) return null;

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-5 border-b border-gray-800">
          <h1 className="text-lg font-bold text-blue-400">Server Console</h1>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map(({ path, label, icon }) => (
            <button
              key={path}
              onClick={() => router.push(path)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-sm flex items-center gap-3 transition-colors ${
                router.pathname === path
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >
              <span className="text-base">{icon}</span>
              {label}
            </button>
          ))}
        </nav>
        <div className="p-3 border-t border-gray-800">
          <button onClick={logout} className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-500 hover:text-red-400 hover:bg-gray-800 transition-colors">
            ⏻ Logout
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
