import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

const ACCEPT = ".txt,.doc,.docx,.pdf,.xls,.xlsx";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleString();
}

export default function FileGallery({ projectId }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const loadFiles = async () => {
    try {
      const data = await api.listFiles(projectId);
      setFiles(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, [projectId]);

  const handleUpload = async (e) => {
    const selected = e.target.files;
    if (!selected || selected.length === 0) return;

    setUploading(true);
    setError(null);
    const formData = new FormData();
    for (const file of selected) {
      formData.append("files", file);
    }

    try {
      await api.uploadFiles(projectId, formData);
      await loadFiles();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleDelete = async (fileId, fileName) => {
    if (!window.confirm(`Delete "${fileName}"?`)) return;
    try {
      await api.deleteFile(projectId, fileId);
      setFiles((prev) => prev.filter((f) => f.id !== fileId));
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <p className="text-sm text-gray-500">Loading files...</p>;

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <label className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 cursor-pointer text-sm">
          {uploading ? "Uploading..." : "Upload Files"}
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPT}
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
          />
        </label>
        <span className="text-xs text-gray-400">TXT, DOC, DOCX, PDF, XLS, XLSX</span>
      </div>

      {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

      {files.length === 0 ? (
        <p className="text-sm text-gray-400">Nessun file caricato</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="py-2 pr-4">Name</th>
              <th className="py-2 pr-4">Type</th>
              <th className="py-2 pr-4">Size</th>
              <th className="py-2 pr-4">Uploaded</th>
              <th className="py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.id} className="border-b hover:bg-gray-50">
                <td className="py-2 pr-4 font-medium truncate max-w-xs" title={f.original_name}>
                  {f.original_name}
                </td>
                <td className="py-2 pr-4 text-gray-500 uppercase">{f.file_type}</td>
                <td className="py-2 pr-4 text-gray-500">{formatSize(f.file_size)}</td>
                <td className="py-2 pr-4 text-gray-500">{formatDate(f.created_at)}</td>
                <td className="py-2 flex gap-2">
                  <a
                    href={api.getFileDownloadUrl(projectId, f.id)}
                    className="text-blue-600 hover:text-blue-800"
                    download
                  >
                    Download
                  </a>
                  <button
                    onClick={() => handleDelete(f.id, f.original_name)}
                    className="text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
