/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect } from 'react';
import AuthForm from './AuthForm';

export default function AuthModal({ isOpen, onClose, initialTab = 'login', onAuthSuccess }) {
  // Lock body scroll when modal is active to prevent scroll chaining
  useEffect(() => {
    if (isOpen) {
      const prevOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      const handleKeyDown = (e) => {
        if (e.key === 'Escape') onClose?.();
      };
      window.addEventListener('keydown', handleKeyDown);
      return () => {
        document.body.style.overflow = prevOverflow;
        window.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-start sm:items-center justify-center p-3 sm:p-4 overscroll-contain">
      <div
        className="fixed inset-0"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative z-10 w-full max-w-md my-auto sm:my-8 animate-in fade-in zoom-in-95 duration-150">
        <AuthForm
          initialTab={initialTab}
          onClose={onClose}
          onAuthSuccess={() => {
            onAuthSuccess?.();
            onClose();
          }}
        />
      </div>
    </div>
  );
}
