import { useEffect, useState } from "react";
import { api } from "../api/client";

const TABS = ["Server", "Tool Descriptions", "Response Messages"];

function getCategory(key) {
  if (key.startsWith("server.")) return "Server";
  if (key.endsWith(".description")) return "Tool Descriptions";
  if (key.endsWith(".response_message")) return "Response Messages";
  return "Other";
}

function formatLabel(key) {
  const parts = key.split(".");
  if (parts[0] === "tool") {
    return parts[1].replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
  if (parts[0] === "server") {
    return parts[1].replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
  return key;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState([]);
  const [edited, setEdited] = useState({});
  const [saving, setSaving] = useState({});
  const [activeTab, setActiveTab] = useState("Server");
  const [resetConfirm, setResetConfirm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getSettings()
      .then(setSettings)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const getValue = (s) => (edited[s.key] !== undefined ? edited[s.key] : s.value);

  const isDirty = (s) => edited[s.key] !== undefined && edited[s.key] !== s.value;

  const handleSave = async (setting) => {
    setSaving((prev) => ({ ...prev, [setting.key]: true }));
    try {
      const updated = await api.updateSetting(setting.key, getValue(setting));
      setSettings((prev) => prev.map((s) => (s.key === setting.key ? updated : s)));
      setEdited((prev) => {
        const next = { ...prev };
        delete next[setting.key];
        return next;
      });
    } catch (e) {
      alert(e.message);
    } finally {
      setSaving((prev) => {
        const next = { ...prev };
        delete next[setting.key];
        return next;
      });
    }
  };

  const handleReset = async (setting) => {
    try {
      await api.resetSetting(setting.key);
      setSettings((prev) =>
        prev.map((s) =>
          s.key === setting.key ? { ...s, value: s.default, is_customized: false } : s
        )
      );
      setEdited((prev) => {
        const next = { ...prev };
        delete next[setting.key];
        return next;
      });
    } catch (e) {
      alert(e.message);
    }
  };

  const handleResetAll = async () => {
    try {
      await api.resetAllSettings();
      setSettings((prev) =>
        prev.map((s) => ({ ...s, value: s.default, is_customized: false }))
      );
      setEdited({});
      setResetConfirm(false);
    } catch (e) {
      alert(e.message);
    }
  };

  const filteredSettings = settings.filter((s) => getCategory(s.key) === activeTab);

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {/* Tabs */}
      <div className="flex gap-0 mb-6 border-b">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Description changes warning */}
      {activeTab === "Tool Descriptions" && (
        <div className="mb-5 p-3 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
          Le modifiche alle descrizioni dei tool hanno effetto dopo il riavvio del backend.
        </div>
      )}

      {/* Settings list */}
      <div className="space-y-5">
        {filteredSettings.length === 0 && (
          <p className="text-gray-500 text-sm">Nessun setting in questa categoria.</p>
        )}
        {filteredSettings.map((setting) => (
          <div key={setting.key} className="border rounded-lg p-4 bg-white">
            <div className="flex items-center justify-between mb-2">
              <label className="font-medium text-sm text-gray-800">
                {formatLabel(setting.key)}
              </label>
              <div className="flex items-center gap-2">
                {setting.is_customized && (
                  <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full font-medium">
                    Customized
                  </span>
                )}
                {setting.is_customized && (
                  <button
                    onClick={() => handleReset(setting)}
                    title="Ripristina valore predefinito"
                    className="text-gray-400 hover:text-gray-600 text-base leading-none"
                  >
                    ↺
                  </button>
                )}
              </div>
            </div>
            <textarea
              value={getValue(setting)}
              onChange={(e) =>
                setEdited((prev) => ({ ...prev, [setting.key]: e.target.value }))
              }
              rows={setting.key.endsWith(".description") ? 4 : 5}
              className="w-full border rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
            {!setting.is_customized && (
              <p className="text-xs text-gray-400 mt-1">Valore predefinito</p>
            )}
            <div className="flex justify-end mt-2">
              <button
                onClick={() => handleSave(setting)}
                disabled={saving[setting.key] || !isDirty(setting)}
                className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving[setting.key] ? "Salvataggio..." : "Save"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Reset all */}
      <div className="mt-8 pt-6 border-t">
        {resetConfirm ? (
          <div className="flex items-center gap-3">
            <p className="text-sm text-gray-600">
              Ripristinare tutti i setting ai valori predefiniti?
            </p>
            <button
              onClick={handleResetAll}
              className="bg-red-600 text-white px-3 py-1.5 rounded text-sm hover:bg-red-700"
            >
              Conferma
            </button>
            <button
              onClick={() => setResetConfirm(false)}
              className="px-3 py-1.5 rounded text-sm border hover:bg-gray-50"
            >
              Annulla
            </button>
          </div>
        ) : (
          <button
            onClick={() => setResetConfirm(true)}
            className="text-sm text-red-600 hover:text-red-800"
          >
            Ripristina tutti i valori predefiniti
          </button>
        )}
      </div>
    </div>
  );
}
