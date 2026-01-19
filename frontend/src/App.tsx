import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Dashboard } from './pages/Dashboard';
import { NotesListPage } from './pages/NotesListPage';
import { NoteDetailPage } from './pages/NoteDetailPage';
import { NotesInsightsPage } from './pages/NotesInsightsPage';
import { SLAPage } from './pages/SLAPage';
import { ExportsPage } from './pages/ExportsPage';
import { LoginPage } from './pages/LoginPage';

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

function AppContent() {
  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-gray-900">
              ProductBoard Insights
            </h1>
            <div className="flex space-x-6">
              <NavLink to="/">Dashboard</NavLink>
              <NavLink to="/notes">Notes</NavLink>
              <NavLink to="/insights">Insights</NavLink>
              <NavLink to="/sla">SLA</NavLink>
              <NavLink to="/exports">Exports</NavLink>
              <LogoutButton />
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto">
        <Routes>
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/notes" element={<ProtectedRoute><NotesListPage /></ProtectedRoute>} />
          <Route path="/notes/:id" element={<ProtectedRoute><NoteDetailPage /></ProtectedRoute>} />
          <Route path="/insights" element={<ProtectedRoute><NotesInsightsPage /></ProtectedRoute>} />
          <Route path="/sla" element={<ProtectedRoute><SLAPage /></ProtectedRoute>} />
          <Route path="/exports" element={<ProtectedRoute><ExportsPage /></ProtectedRoute>} />
        </Routes>
      </main>
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
