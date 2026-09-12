/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const recentToastsRef = React.useRef(new Map());

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message, type = 'info', duration = 3500) => {
      if (!message) return null;

      // Chống spam: Nếu thông báo cùng loại và nội dung xuất hiện trong vòng 2.5 giây, bỏ qua không tạo popup trùng
      const now = Date.now();
      const key = `${type}:${message}`;
      const lastShown = recentToastsRef.current.get(key);
      if (lastShown && now - lastShown < 2500) {
        return null;
      }
      recentToastsRef.current.set(key, now);

      const id = `${now}-${Math.random().toString(36).substr(2, 9)}`;
      const newToast = { id, message, type };

      // Giới hạn tối đa 3 popup hiển thị cùng lúc để tránh che khuất giao diện
      setToasts((prev) => [...prev.slice(-2), newToast]);

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
      return id;
    },
    [removeToast]
  );

  const toast = {
    success: (msg, dur) => addToast(msg, 'success', dur),
    error: (msg, dur) => addToast(msg, 'error', dur),
    warning: (msg, dur) => addToast(msg, 'warning', dur),
    info: (msg, dur) => addToast(msg, 'info', dur),
  };

  const showToast = (msg, type = 'info', dur = 3500) => addToast(msg, type, dur);

  return (
    <ToastContext.Provider value={{ toast, showToast, addToast, removeToast }}>
      {children}
      {/* Toast floating container */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0">
        {toasts.map((t) => {
          let bgColor = 'bg-slate-900 text-white border-slate-700';
          let icon = <Info className="w-5 h-5 text-blue-400 flex-shrink-0" />;

          if (t.type === 'success') {
            bgColor = 'bg-emerald-900/95 text-emerald-50 border-emerald-700 shadow-emerald-950/20';
            icon = <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />;
          } else if (t.type === 'error') {
            bgColor = 'bg-red-900/95 text-red-50 border-red-700 shadow-red-950/20';
            icon = <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />;
          } else if (t.type === 'warning') {
            bgColor = 'bg-amber-900/95 text-amber-50 border-amber-700 shadow-amber-950/20';
            icon = <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />;
          }

          return (
            <div
              key={t.id}
              className={`pointer-events-auto flex items-start gap-3 p-4 rounded-2xl border shadow-xl backdrop-blur-md transition-all transform translate-y-0 opacity-100 ${bgColor}`}
            >
              {icon}
              <div className="flex-1 text-sm font-medium leading-snug">
                {t.message}
              </div>
              <button
                onClick={() => removeToast(t.id)}
                className="text-slate-400 hover:text-white transition-colors -mr-1 -mt-1 p-1 rounded-lg"
                title="Đóng"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
