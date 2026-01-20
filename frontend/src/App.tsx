import { useState } from 'react';
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Dashboard } from './pages/Dashboard';
import { NotesListPage } from './pages/NotesListPage';
import { NoteDetailPage } from './pages/NoteDetailPage';
import { NotesInsightsPage } from './pages/NotesInsightsPage';
import { SLAPage } from './pages/SLAPage';
import { LoginPage } from './pages/LoginPage';
import { syncApi } from './api/sync';

const queryClient = new QueryClient();

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  const location = useLocation();
  const isActive = location.pathname === to ||
    (to !== '/' && location.pathname.startsWith(to));

  return (
    <Link
      to={to}
      className={`${
        isActive
          ? 'text-gray-900 font-semibold'
          : 'text-gray-600 hover:text-gray-900'
      }`}
    >
      {children}
    </Link>
  );
}

function LogoutButton() {
  const { logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  return (
    <button
      onClick={handleLogout}
      className="text-gray-600 hover:text-gray-900"
    >
      Logout
    </button>
  );
}

function formatLastSyncTime(isoString: string | undefined): string {
  if (!isoString) return 'Never';

  const date = new Date(isoString);
  const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' });

  // Get timezone abbreviation
  const tzAbbr = new Intl.DateTimeFormat('en', { timeZoneName: 'short' })
    .formatToParts(date)
    .find(part => part.type === 'timeZoneName')?.value || '';

  return `${dateStr} ${timeStr} ${tzAbbr}`;
}

function SyncButton() {
  const queryClient = useQueryClient();
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');

  const { data: syncStatus } = useQuery({
    queryKey: ['sync', 'status'],
    queryFn: () => syncApi.getStatus().then(r => r.data),
    refetchInterval: syncing ? 3000 : 30000,
  });

  const isSyncing = syncing || syncStatus?.status === 'running';

  const handleSync = async () => {
    // Don't trigger if already syncing
    if (isSyncing) {
      setSyncMessage('Sync already in progress');
      setTimeout(() => setSyncMessage(''), 3000);
      return;
    }

    setSyncing(true);
    setSyncMessage('');
    try {
      const response = await syncApi.trigger();

      if (!response.data.triggered) {
        // Sync wasn't triggered (already running)
        setSyncing(false);
        setSyncMessage(response.data.message);
        setTimeout(() => setSyncMessage(''), 3000);
        return;
      }

      setSyncMessage('Syncing...');
      const checkStatus = setInterval(async () => {
        const status = await syncApi.getStatus();
        if (status.data.status === 'idle') {
          clearInterval(checkStatus);
          setSyncing(false);
          setSyncMessage('Sync completed!');
          queryClient.invalidateQueries();
          setTimeout(() => setSyncMessage(''), 5000);
        }
      }, 3000);
    } catch {
      setSyncing(false);
      setSyncMessage('Sync failed');
    }
  };

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-500">
        Last sync: {formatLastSyncTime(syncStatus?.last_sync_at)}
      </span>
      {syncMessage && (
        <span className={`text-sm ${syncMessage.includes('failed') || syncMessage.includes('already') ? 'text-amber-600' : 'text-green-600'}`}>
          {syncMessage}
        </span>
      )}
      <button
        onClick={handleSync}
        disabled={isSyncing}
        className="bg-blue-600 text-white px-3 py-1.5 text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      >
        {isSyncing && (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )}
        {isSyncing ? 'Syncing...' : 'Sync'}
      </button>
    </div>
  );
}

function AppContent() {
  const navigate = useNavigate();

  const handleLogoClick = () => {
    // Reset dashboard period to Last 7 days
    localStorage.setItem('dashboard-period', JSON.stringify({
      periodType: 'preset',
      presetDays: 7,
      customStart: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      customEnd: new Date().toISOString().split('T')[0],
    }));
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={handleLogoClick}
              className="text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors"
            >
              Notes HQ
            </button>
            <div className="flex items-center space-x-6">
              <NavLink to="/">Dashboard</NavLink>
              <NavLink to="/insights">Insights</NavLink>
              <NavLink to="/sla">SLA</NavLink>
              <NavLink to="/notes">Notes</NavLink>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto flex-1 w-full">
        <Routes>
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/notes" element={<ProtectedRoute><NotesListPage /></ProtectedRoute>} />
          <Route path="/notes/:id" element={<ProtectedRoute><NoteDetailPage /></ProtectedRoute>} />
          <Route path="/insights" element={<ProtectedRoute><NotesInsightsPage /></ProtectedRoute>} />
          <Route path="/sla" element={<ProtectedRoute><SLAPage /></ProtectedRoute>} />
        </Routes>
      </main>
      <footer className="bg-white border-t border-gray-200 sticky bottom-0">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-end gap-4">
            <SyncButton />
            <LogoutButton />
          </div>
        </div>
      </footer>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/*" element={<AppContent />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
