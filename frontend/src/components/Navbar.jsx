/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useEffect, useRef } from 'react';
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

  // Fetch notifications periodically or on mount when authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    const fetchNotifs = async () => {
      try {
        const data = await notifApi.get();
        const list = data || [];
        setNotifications(list);
        setUnreadCount(list.filter((n) => !n.read).length);
      } catch {
        // Fallback silently if unauthenticated or network error
      }
    };

    fetchNotifs();
    const timer = setInterval(fetchNotifs, 15000); // 15s poll
    return () => clearInterval(timer);
  }, [isAuthenticated]);

  // Click outside to close notification dropdown
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
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    setUnreadCount(0);
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
                              onClick={() => {
                                setShowNotifDropdown(false);
                                if (n.share_token) {
                                  onSelectInvoice?.(n.share_token);
                                }
                              }}
                              className={`p-3.5 hover:bg-slate-50 cursor-pointer transition-colors space-y-1 ${
                                !n.read ? 'bg-primary-50/40' : ''
                              }`}
                            >
                              <div className="flex items-center justify-between gap-2">
                                <h4 className="text-xs font-bold text-slate-900 leading-tight">
                                  {n.title}
                                </h4>
                                {n.short_code && (
                                  <span className="px-1.5 py-0.5 bg-slate-100 font-mono text-[10px] font-bold text-slate-700 rounded border border-slate-200">
                                    {n.short_code}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-slate-600">{n.message}</p>
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
