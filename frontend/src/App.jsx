import { BrowserRouter, Route, Routes } from "react-router-dom";
import NewProjectPage from "./pages/NewProjectPage";
import NewTaskPage from "./pages/NewTaskPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import TaskDetailPage from "./pages/TaskDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-5xl mx-auto px-4 py-4">
            <a href="/" className="text-xl font-bold text-gray-900">
              Manager AI
            </a>
          </div>
        </header>
        <main className="max-w-5xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<ProjectsPage />} />
            <Route path="/projects/new" element={<NewProjectPage />} />
            <Route path="/projects/:id" element={<ProjectDetailPage />} />
            <Route path="/projects/:id/tasks/new" element={<NewTaskPage />} />
            <Route path="/projects/:id/tasks/:taskId" element={<TaskDetailPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
