import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';

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
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
