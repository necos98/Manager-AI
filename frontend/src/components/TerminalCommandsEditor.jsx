import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function TerminalCommandsEditor({ projectId = null }) {
  const [commands, setCommands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newCmd, setNewCmd] = useState("");

  const load = () => {
    setLoading(true);
    api
      .listTerminalCommands(projectId)
      .then(setCommands)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [projectId]);

  const handleAdd = async () => {
    const trimmed = newCmd.trim();
    if (!trimmed) return;
    const sortOrder = commands.length > 0 ? Math.max(...commands.map((c) => c.sort_order)) + 1 : 0;
    await api.createTerminalCommand({
      command: trimmed,
      sort_order: sortOrder,
      project_id: projectId,
    });
    setNewCmd("");
    load();
  };

  const handleDelete = async (id) => {
    await api.deleteTerminalCommand(id);
    load();
  };

  const handleBlur = async (cmd, newValue) => {
    const trimmed = newValue.trim();
    if (!trimmed || trimmed === cmd.command) return;
    await api.updateTerminalCommand(cmd.id, { command: trimmed });
    load();
  };

  const handleMove = async (index, direction) => {
    const swapIndex = index + direction;
    if (swapIndex < 0 || swapIndex >= commands.length) return;
    const reordered = [
      { id: commands[index].id, sort_order: commands[swapIndex].sort_order },
      { id: commands[swapIndex].id, sort_order: commands[index].sort_order },
    ];
    await api.reorderTerminalCommands(reordered);
    load();
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  if (loading) return <p className="text-sm text-gray-500">Loading...</p>;

  return (
    <div className="space-y-2">
      {commands.length === 0 && projectId != null && (
        <p className="text-sm text-gray-500 italic">
          No project commands configured. Global commands will be used.
        </p>
      )}

      {commands.map((cmd, index) => (
        <div key={cmd.id} className="flex items-center gap-2">
          <div className="flex flex-col">
            <button
              onClick={() => handleMove(index, -1)}
              disabled={index === 0}
              className="text-gray-400 hover:text-gray-600 text-xs leading-none disabled:opacity-30 disabled:cursor-not-allowed"
              title="Move up"
            >
              ▲
            </button>
            <button
              onClick={() => handleMove(index, 1)}
              disabled={index === commands.length - 1}
              className="text-gray-400 hover:text-gray-600 text-xs leading-none disabled:opacity-30 disabled:cursor-not-allowed"
              title="Move down"
            >
              ▼
            </button>
          </div>
          <input
            type="text"
            defaultValue={cmd.command}
            onBlur={(e) => handleBlur(cmd, e.target.value)}
            className="flex-1 border rounded px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          <button
            onClick={() => handleDelete(cmd.id)}
            className="text-gray-400 hover:text-red-600 text-lg leading-none"
            title="Delete"
          >
            &times;
          </button>
        </div>
      ))}

      <div className="flex gap-2 mt-3">
        <input
          type="text"
          value={newCmd}
          onChange={(e) => setNewCmd(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a command..."
          className="flex-1 border rounded px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
        <button
          onClick={handleAdd}
          disabled={!newCmd.trim()}
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add
        </button>
      </div>
    </div>
  );
}
