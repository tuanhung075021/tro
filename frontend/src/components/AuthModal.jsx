/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React from 'react';
import AuthForm from './AuthForm';

export default function AuthModal({ isOpen, onClose, initialTab = 'login', onAuthSuccess }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className="fixed inset-0"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative z-10 w-full max-w-md my-8 animate-in fade-in zoom-in-95 duration-150">
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
