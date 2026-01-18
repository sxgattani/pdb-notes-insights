import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { NotesListPage } from './pages/NotesListPage';
import { NoteDetailPage } from './pages/NoteDetailPage';
import { FeaturesListPage } from './pages/FeaturesListPage';
import { FeatureDetailPage } from './pages/FeatureDetailPage';
import { WorkloadPage } from './pages/WorkloadPage';
import { SLAPage } from './pages/SLAPage';

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
              <NavLink to="/features">Features</NavLink>
              <NavLink to="/workload">Workload</NavLink>
              <NavLink to="/sla">SLA</NavLink>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/notes" element={<NotesListPage />} />
          <Route path="/notes/:id" element={<NoteDetailPage />} />
          <Route path="/features" element={<FeaturesListPage />} />
          <Route path="/features/:id" element={<FeatureDetailPage />} />
          <Route path="/workload" element={<WorkloadPage />} />
          <Route path="/sla" element={<SLAPage />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
