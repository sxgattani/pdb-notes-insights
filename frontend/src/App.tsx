import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { NotesListPage } from './pages/NotesListPage';
import { NoteDetailPage } from './pages/NoteDetailPage';
import { FeaturesListPage } from './pages/FeaturesListPage';
import { FeatureDetailPage } from './pages/FeatureDetailPage';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-100">
          <nav className="bg-white shadow">
            <div className="max-w-7xl mx-auto px-4 py-4">
              <h1 className="text-xl font-bold text-gray-900">
                ProductBoard Insights
              </h1>
            </div>
          </nav>
          <main className="max-w-7xl mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/notes" element={<NotesListPage />} />
              <Route path="/notes/:id" element={<NoteDetailPage />} />
              <Route path="/features" element={<FeaturesListPage />} />
              <Route path="/features/:id" element={<FeatureDetailPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
