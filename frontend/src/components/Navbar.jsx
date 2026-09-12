/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { notifications as notifApi } from '../services/api';
import {
  Zap,
  LogOut,
  Building2,
  UserCheck,
  ShieldCheck,
  FileText,
  Scale,
  Bell,
  CheckCheck,
  ExternalLink,
  FileCheck2,
  FileClock,
} from 'lucide-react';

export default function Navbar({
  currentView,
  setCurrentView,
  onOpenTariffModal,
  onOpenAuthModal,
  onSelectInvoice,
}) {
  const { user, isAuthenticated, isLandlord, isTenant, logout } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifDropdown, setShowNotifDropdown] = useState(false);
  const dropdownRef = useRef(null);
  // Persist read IDs across re-fetches using a Set in a ref
  const readIdsRef = useRef(new Set());

  const fetchNotifs = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const data = await notifApi.get();
      const list = (data || []).map((n) => ({
        ...n,
        read: readIdsRef.current.has(n.id) ? true : n.read,
      }));
      setNotifications(list);
      setUnreadCount(list.filter((n) => !n.read).length);
    } catch {
      // Fail silently on network error / unauthenticated
    }
  }, [isAuthenticated]);

  // Fetch notifications on mount and every 30s
  useEffect(() => {
    if (!isAuthenticated) {
      setNotifications([]);
      setUnreadCount(0);
      readIdsRef.current.clear();
      return;
    }

    fetchNotifs();
    const timer = setInterval(fetchNotifs, 30000); // 30s poll (reduced from 15s)
    return () => clearInterval(timer);
  }, [isAuthenticated, fetchNotifs]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowNotifDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkAllRead = () => {
    setNotifications((prev) => {
      const updated = prev.map((n) => {
        readIdsRef.current.add(n.id);
        return { ...n, read: true };
      });
      return updated;
    });
    setUnreadCount(0);
  };

  const handleNotifClick = (n) => {
    // Mark this one as read
    readIdsRef.current.add(n.id);
    setNotifications((prev) =>
      prev.map((x) => (x.id === n.id ? { ...x, read: true } : x))
    );
    setUnreadCount((c) => Math.max(0, c - (n.read ? 0 : 1)));
    setShowNotifDropdown(false);
    if (n.share_token) {
      onSelectInvoice?.(n.share_token);
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return null;
    try {
      const d = new Date(ts);
      const now = new Date();
      const diffMs = now - d;
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Vừa xong';
      if (diffMins < 60) return `${diffMins} phút trước`;
      const diffHrs = Math.floor(diffMins / 60);
      if (diffHrs < 24) return `${diffHrs} giờ trước`;
      const diffDays = Math.floor(diffHrs / 24);
      if (diffDays < 7) return `${diffDays} ngày trước`;
      return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch {
      return null;
    }
  };

  const getNotifStyle = (type, isRead) => {
    const base = isRead ? 'bg-white' : '';
    if (type === 'invoice_draft') return `${isRead ? 'bg-white' : 'bg-amber-50/60'}`;
    if (type === 'invoice_published') return `${isRead ? 'bg-white' : 'bg-emerald-50/60'}`;
    return base;
  };

  const getNotifIcon = (type) => {
    if (type === 'invoice_draft')
      return <FileClock className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />;
    if (type === 'invoice_published')
      return <FileCheck2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />;
    return <FileText className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />;
  };

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-slate-200 shadow-sm">
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
              </div>
              <p className="text-[11px] text-slate-500 hidden md:block">
                Hệ thống Quản lý Lưu trú & Đối chiếu Chi phí Điện Nước Minh bạch
              </p>
            </div>
          </div>

          {/* Center / Nav Items */}
          <nav className="flex items-center gap-1 sm:gap-2">
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

            {/* Single Consolidated Tariff Modal Button */}
            <button
              onClick={onOpenTariffModal}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs sm:text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 rounded-lg transition-colors"
            >
              <Scale className="w-4 h-4 text-slate-500" />
              <span>Biểu giá quy định</span>
            </button>
          </nav>

          {/* User Profile / Status / Logout */}
          <div className="flex items-center gap-2 sm:gap-3">
            {isAuthenticated && user ? (
              <>
                {/* Notification Bell Dropdown */}
                <div className="relative" ref={dropdownRef}>
                  <button
                    onClick={() => setShowNotifDropdown((prev) => !prev)}
                    className="relative p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-colors"
                    title="Thông báo"
                  >
                    <Bell className="w-5 h-5" />
                    {unreadCount > 0 && (
                      <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-red-500 rounded-full ring-2 ring-white animate-pulse" />
                    )}
                  </button>

                  {/* Dropdown panel */}
                  {showNotifDropdown && (
                    <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-150">
                      <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Bell className="w-4 h-4 text-primary-600" />
                          <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                            Thông báo
                          </span>
                          {unreadCount > 0 && (
                            <span className="px-1.5 py-0.2 bg-red-100 text-red-700 text-[10px] font-black rounded-full">
                              {unreadCount}
                            </span>
                          )}
                        </div>
                        {notifications.length > 0 && (
                          <button
                            onClick={handleMarkAllRead}
                            className="text-[11px] font-semibold text-primary-600 hover:text-primary-700 flex items-center gap-1"
                          >
                            <CheckCheck className="w-3.5 h-3.5" />
                            <span>Đã đọc tất cả</span>
                          </button>
                        )}
                      </div>

                      <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                        {notifications.length === 0 ? (
                          <div className="p-8 text-center text-xs text-slate-400">
                            Chưa có thông báo mới nào
                          </div>
                        ) : (
                          notifications.map((n) => (
                            <div
                              key={n.id}
                              onClick={() => handleNotifClick(n)}
                              className={`p-3.5 hover:bg-slate-50 cursor-pointer transition-colors ${getNotifStyle(n.type, n.read)}`}
                            >
                              <div className="flex items-start gap-2.5">
                                {getNotifIcon(n.type)}
                                <div className="flex-1 min-w-0 space-y-0.5">
                                  <div className="flex items-start justify-between gap-2">
                                    <h4 className={`text-xs font-bold leading-tight ${n.read ? 'text-slate-600' : 'text-slate-900'}`}>
                                      {n.title}
                                    </h4>
                                    {n.short_code && (
                                      <span className="flex-shrink-0 px-1.5 py-0.5 bg-slate-100 font-mono text-[10px] font-bold text-slate-600 rounded border border-slate-200">
                                        {n.short_code}
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-xs text-slate-500 leading-snug">{n.message}</p>
                                  {n.timestamp && (
                                    <p className="text-[10px] text-slate-400">{formatTimestamp(n.timestamp)}</p>
                                  )}
                                </div>
                                {!n.read && (
                                  <span className="w-2 h-2 bg-primary-500 rounded-full flex-shrink-0 mt-1" />
                                )}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>

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
                onClick={onOpenAuthModal}
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
