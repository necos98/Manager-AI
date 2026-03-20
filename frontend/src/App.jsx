import { useEffect, useState } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import NewProjectPage from "./pages/NewProjectPage";
import NewIssuePage from "./pages/NewIssuePage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import IssueDetailPage from "./pages/IssueDetailPage";
import TerminalsPage from "./pages/TerminalsPage";
import SettingsPage from "./pages/SettingsPage";

function Navbar() {
  const [terminalCount, setTerminalCount] = useState(0);

  useEffect(() => {
    const fetchCount = () => {
      api.terminalCount().then((data) => setTerminalCount(data.count)).catch(() => {});
    };
    fetchCount();
    const interval = setInterval(fetchCount, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
        <a href="/" className="text-xl font-bold text-gray-900">
          Manager AI
        </a>
        <div className="flex items-center gap-4">
          <Link to="/terminals" className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1.5">
            Terminals
            {terminalCount > 0 && (
              <span className="bg-green-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                {terminalCount}
              </span>
            )}
          </Link>
          <Link to="/settings" className="text-sm text-gray-500 hover:text-gray-900">
            Settings
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="max-w-5xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<ProjectsPage />} />
            <Route path="/projects/new" element={<NewProjectPage />} />
            <Route path="/projects/:id" element={<ProjectDetailPage />} />
            <Route path="/projects/:id/issues/new" element={<NewIssuePage />} />
            <Route path="/projects/:id/issues/:issueId" element={<IssueDetailPage />} />
            <Route path="/terminals" element={<TerminalsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
