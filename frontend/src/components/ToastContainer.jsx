import { useEffect, useRef, useState } from "react";

function Toast({ toast, onDismiss, onClick }) {
  const [visible, setVisible] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    // Trigger fade-in on next frame
    const frame = requestAnimationFrame(() => setVisible(true));

    timerRef.current = setTimeout(() => {
      setVisible(false);
      // Wait for fade-out transition before removing
      setTimeout(() => onDismiss(toast.id), 300);
    }, 8000);

    return () => {
      cancelAnimationFrame(frame);
      clearTimeout(timerRef.current);
    };
  }, [toast.id, onDismiss]);

  return (
    <div
      onClick={() => onClick(toast)}
      className="cursor-pointer bg-white shadow-lg rounded-lg border-l-4 border-blue-500 p-4 max-w-sm w-full flex items-start gap-3"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(8px)",
        transition: "opacity 0.3s ease, transform 0.3s ease",
      }}
    >
      <div className="flex-1 min-w-0">
        {toast.title && (
          <p className="text-sm font-semibold text-gray-900 truncate">
            {toast.title}
          </p>
        )}
        {toast.issue_name && (
          <p className="text-sm text-gray-600 truncate mt-0.5">
            {toast.issue_name}
          </p>
        )}
        {!toast.title && !toast.issue_name && (
          <p className="text-sm text-gray-600">New notification</p>
        )}
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDismiss(toast.id);
        }}
        className="text-gray-400 hover:text-gray-600 flex-shrink-0 mt-0.5"
        aria-label="Dismiss"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

export default function ToastContainer({ toasts, onDismiss, onToastClick }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col-reverse gap-2 items-end pointer-events-none">
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <Toast toast={toast} onDismiss={onDismiss} onClick={onToastClick} />
        </div>
      ))}
    </div>
  );
}
