/*
 * Copyright (c) 2026 tro Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useEffect, useCallback } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import AuthForm from './components/AuthForm';
import LandlordDashboard from './components/LandlordDashboard';
import TenantDashboard from './components/TenantDashboard';
import PublicInvoiceView from './components/PublicInvoiceView';
import { Zap, ShieldCheck, FileText, Scale, Heart } from 'lucide-react';

function MainLayout() {
  const { user, isAuthenticated, isLandlord, isTenant, loading } = useAuth();
  const [currentView, setCurrentView] = useState('home'); // 'home' | 'auth' | 'public'
  const [publicToken, setPublicToken] = useState('');

  // Extract public token from URL (path /public/:token, hash #public/:token, or search ?public=token)
  const parseUrlRoute = useCallback(() => {
    const pathname = window.location.pathname;
    const searchParams = new URLSearchParams(window.location.search);
    const hash = window.location.hash;

    // Check query params: ?public=xyz or ?token=xyz
    const queryToken = searchParams.get('public') || searchParams.get('token');
    if (queryToken) {
      setPublicToken(queryToken);
      setCurrentView('public');
      return;
    }

    // Check path: /public/:token
    const publicMatch = pathname.match(/^\/public\/([^/?#]+)/);
    if (publicMatch && publicMatch[1]) {
      setPublicToken(decodeURIComponent(publicMatch[1]));
      setCurrentView('public');
      return;
    }

    // Check path: /public or /public/ (open search portal)
    if (pathname === '/public' || pathname === '/public/') {
      setPublicToken('');
      setCurrentView('public');
      return;
    }

    // Check hash: #public/:token or #/public/:token
    const hashMatch = hash.match(/^#\/?public\/([^/?#]+)/);
    if (hashMatch && hashMatch[1]) {
      setPublicToken(decodeURIComponent(hashMatch[1]));
      setCurrentView('public');
      return;
    }

    // Fallback: When navigating back to root or other non-public URLs
    setPublicToken('');
    setCurrentView((prev) => (prev === 'public' ? 'home' : prev));
  }, []);

  useEffect(() => {
    parseUrlRoute();

    const handleLocationChange = () => {
      parseUrlRoute();
    };

    window.addEventListener('popstate', handleLocationChange);
    window.addEventListener('hashchange', handleLocationChange);

    return () => {
      window.removeEventListener('popstate', handleLocationChange);
      window.removeEventListener('hashchange', handleLocationChange);
    };
  }, [parseUrlRoute]);

  const handleViewPublicInvoice = (shareToken) => {
    setPublicToken(shareToken);
    setCurrentView('public');
    window.history.pushState(null, '', `/public/${encodeURIComponent(shareToken)}`);
  };

  const handleBackToHome = () => {
    setPublicToken('');
    setCurrentView('home');
    window.history.pushState(null, '', '/');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-600 text-white shadow-xl shadow-primary-500/25 animate-pulse">
            <Zap className="w-7 h-7 fill-current" />
          </div>
          <p className="text-sm font-bold text-slate-700">Đang khởi tạo hệ thống tro...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between">
      <div>
        <Navbar currentView={currentView} setCurrentView={setCurrentView} />

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* VIEW ROUTER */}
          {currentView === 'public' ? (
            <PublicInvoiceView initialToken={publicToken} onBackToHome={handleBackToHome} />
          ) : !isAuthenticated ? (
            <div className="py-6 sm:py-12 space-y-12">
              {/* Hero Banner for Unauthenticated Users */}
              <div className="text-center max-w-3xl mx-auto space-y-4">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-100 text-primary-800 text-xs font-bold border border-primary-200">
                  <ShieldCheck className="w-4 h-4 text-primary-600" />
                  <span>Tuân thủ Nghị quyết 204/2025/QH15 & Nghị định 104/2022/NĐ-CP</span>
                </div>
                <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight leading-tight">
                  Minh bạch chi phí điện nước <br className="hidden sm:inline" />
                  <span className="text-primary-600">bảo vệ chủ trọ và người thuê</span>
                </h1>
                <p className="text-slate-600 text-sm sm:text-base leading-relaxed">
                  Hệ thống tự động tính giá bán lẻ điện sinh hoạt 6 bậc thang, đối chiếu tiền thực thu với quy định pháp luật và cung cấp cổng tra cứu công khai tức thì.
                </p>
              </div>

              {/* Login / Register Card */}
              <AuthForm onAuthSuccess={() => setCurrentView('home')} />
            </div>
          ) : isLandlord ? (
            <LandlordDashboard onViewPublicInvoice={handleViewPublicInvoice} />
          ) : isTenant ? (
            <TenantDashboard onViewPublicInvoice={handleViewPublicInvoice} />
          ) : (
            <div className="p-8 bg-white rounded-3xl border border-slate-200 text-center">
              <p className="text-slate-700 font-bold">Tài khoản chưa được phân vai trò hợp lệ.</p>
            </div>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="mt-16 bg-white border-t border-slate-200 py-8 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-base font-black text-slate-900">
              tro<span className="text-primary-600">.</span>
            </span>
            <span>— Hệ thống tính toán và đối chiếu chi phí điện nước nhà trọ minh bạch.</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 text-[11px] text-slate-400">
            <span>Giấy phép mã nguồn mở MIT</span>
            <span>•</span>
            <span>Thông tư 60/2025/TT-BCT</span>
            <span>•</span>
            <span>Quyết định 1279/QĐ-BCT</span>
            <span>•</span>
            <span>Nghị định 104/2022/NĐ-CP</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  );
}
