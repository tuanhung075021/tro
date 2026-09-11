/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Zap, LogOut, Building2, UserCheck, ShieldCheck, FileText } from 'lucide-react';

export default function Navbar({ currentView, setCurrentView }) {
  const { user, isAuthenticated, isLandlord, isTenant, logout } = useAuth();

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Slogan */}
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => {
              setCurrentView?.('home');
              window.history.pushState(null, '', '/');
            }}
          >
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary-600 text-white shadow-md shadow-primary-500/20">
              <Zap className="w-5 h-5 fill-current" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-2xl font-black tracking-tight text-slate-900">
                  tro<span className="text-primary-600">.</span>
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase rounded-full bg-primary-100 text-primary-800 border border-primary-200">
                  Minh bạch
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden md:block">
                Minh bạch chi phí điện nước nhà trọ
              </p>
            </div>
          </div>

          {/* Center / Nav Items */}
          <nav className="flex items-center gap-2">
            <button
              onClick={() => {
                setCurrentView?.('public');
                window.history.pushState(null, '', '/public');
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs sm:text-sm font-medium rounded-lg transition-colors ${
                currentView === 'public'
                  ? 'bg-slate-100 text-slate-900'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <FileText className="w-4 h-4 text-slate-500" />
              <span>Tra cứu công khai</span>
            </button>
          </nav>

          {/* User Profile / Status / Logout */}
          <div className="flex items-center gap-3">
            {isAuthenticated && user ? (
              <>
                <div className="flex items-center gap-2">
                  {/* Role Badge */}
                  {isLandlord && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                      <Building2 className="w-3.5 h-3.5" />
                      <span>Chủ trọ</span>
                    </span>
                  )}
                  {isTenant && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 border border-blue-300">
                      <UserCheck className="w-3.5 h-3.5" />
                      <span>Người thuê</span>
                    </span>
                  )}

                  {/* User Name */}
                  <div className="hidden lg:block text-right">
                    <p className="text-sm font-semibold text-slate-800 leading-tight">
                      {user.full_name || user.username}
                    </p>
                    <p className="text-xs text-slate-500">@{user.username}</p>
                  </div>
                </div>

                {/* Logout Button */}
                <button
                  onClick={logout}
                  title="Đăng xuất"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs sm:text-sm font-medium text-slate-700 bg-slate-100 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors border border-slate-200"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="hidden sm:inline">Đăng xuất</span>
                </button>
              </>
            ) : (
              <button
                onClick={() => setCurrentView?.('auth')}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs sm:text-sm font-semibold text-white bg-primary-600 hover:bg-primary-700 rounded-lg shadow-sm transition-all"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Đăng nhập / Đăng ký</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
