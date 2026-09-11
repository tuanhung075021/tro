/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Zap,
  Lock,
  User,
  Phone,
  ShieldCheck,
  Building2,
  UserCheck,
  KeyRound,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';

export default function AuthForm({ initialTab = 'login', onAuthSuccess }) {
  const { login, register, authError } = useAuth();
  const [tab, setTab] = useState(initialTab); // 'login' | 'register'
  const [role, setRole] = useState('landlord'); // 'landlord' | 'tenant'
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  // Form states
  const [loginData, setLoginData] = useState({ username: '', password: '' });
  const [registerData, setRegisterData] = useState({
    username: '',
    password: '',
    full_name: '',
    phone: '',
    invite_code: '',
  });

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await login(loginData.username.trim(), loginData.password);
      onAuthSuccess?.();
    } catch (err) {
      setFormError(err.message || 'Đăng nhập không thành công');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      const cleanInvite = registerData.invite_code.trim().toUpperCase();
      const payload = {
        username: registerData.username.trim(),
        password: registerData.password,
        full_name: registerData.full_name.trim(),
        phone: registerData.phone.trim() || undefined,
        role: role,
        invite_code: role === 'tenant' && cleanInvite ? cleanInvite : undefined,
      };

      await register(payload);
      onAuthSuccess?.();
    } catch (err) {
      setFormError(err.message || 'Đăng ký không thành công');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200/80 overflow-hidden">
        {/* Header decoration */}
        <div className="bg-gradient-to-r from-primary-600 via-emerald-600 to-teal-700 px-6 py-8 text-white text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-white/10 backdrop-blur border border-white/20 mb-3 shadow-inner">
            <Zap className="w-7 h-7 text-primary-200 fill-current" />
          </div>
          <h2 className="text-2xl font-black tracking-tight">tro.</h2>
          <p className="text-emerald-100 text-sm mt-1">
            Nền tảng đối chiếu chi phí điện nước minh bạch số #1
          </p>
        </div>

        {/* Tab switchers */}
        <div className="grid grid-cols-2 border-b border-slate-200 text-sm font-semibold bg-slate-50/50">
          <button
            type="button"
            onClick={() => {
              setTab('login');
              setFormError(null);
            }}
            className={`py-3.5 text-center transition-all ${
              tab === 'login'
                ? 'bg-white text-primary-700 border-b-2 border-primary-600 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Đăng nhập
          </button>
          <button
            type="button"
            onClick={() => {
              setTab('register');
              setFormError(null);
            }}
            className={`py-3.5 text-center transition-all ${
              tab === 'register'
                ? 'bg-white text-primary-700 border-b-2 border-primary-600 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Đăng ký tài khoản
          </button>
        </div>

        <div className="p-6 sm:p-8">
          {/* Error display */}
          {(formError || authError) && (
            <div className="mb-5 p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs sm:text-sm text-red-700 flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="leading-snug">{formError || authError}</div>
            </div>
          )}

          {/* LOGIN FORM */}
          {tab === 'login' && (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Tên đăng nhập
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
                  <input
                    type="text"
                    required
                    value={loginData.username}
                    onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                    placeholder="Ví dụ: chuto123"
                    className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Mật khẩu
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
                  <input
                    type="password"
                    required
                    value={loginData.password}
                    onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                    placeholder="Nhập mật khẩu của bạn"
                    className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full mt-2 py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-semibold rounded-xl shadow-md shadow-primary-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <span className="inline-block animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                ) : (
                  <>
                    <span>Đăng nhập ngay</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* REGISTER FORM */}
          {tab === 'register' && (
            <form onSubmit={handleRegisterSubmit} className="space-y-4">
              {/* Role Selection */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                  Bạn là:
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setRole('landlord')}
                    className={`p-3 rounded-xl border flex flex-col items-center gap-1.5 transition-all text-xs font-semibold ${
                      role === 'landlord'
                        ? 'border-primary-600 bg-primary-50 text-primary-900 ring-2 ring-primary-500/20'
                        : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <Building2 className={`w-5 h-5 ${role === 'landlord' ? 'text-primary-600' : 'text-slate-400'}`} />
                    <span>Chủ nhà trọ</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setRole('tenant')}
                    className={`p-3 rounded-xl border flex flex-col items-center gap-1.5 transition-all text-xs font-semibold ${
                      role === 'tenant'
                        ? 'border-brandblue-600 bg-brandblue-50 text-brandblue-900 ring-2 ring-brandblue-500/20'
                        : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <UserCheck className={`w-5 h-5 ${role === 'tenant' ? 'text-brandblue-600' : 'text-slate-400'}`} />
                    <span>Người thuê trọ</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Họ và tên
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
                  <input
                    type="text"
                    required
                    value={registerData.full_name}
                    onChange={(e) => setRegisterData({ ...registerData, full_name: e.target.value })}
                    placeholder="Nguyễn Văn A"
                    className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Tên đăng nhập
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
                  <input
                    type="text"
                    required
                    value={registerData.username}
                    onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })}
                    placeholder="nguyenvana"
                    className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Mật khẩu
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
                  <input
                    type="password"
                    required
                    value={registerData.password}
                    onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                    placeholder="Tối thiểu 6 ký tự"
                    className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Số điện thoại (tuỳ chọn)
                </label>
                <div className="relative">
                  <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
                  <input
                    type="tel"
                    value={registerData.phone}
                    onChange={(e) => setRegisterData({ ...registerData, phone: e.target.value })}
                    placeholder="0912345678"
                    className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              {/* Invite code for tenant */}
              {role === 'tenant' && (
                <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl space-y-1.5">
                  <label className="block text-xs font-bold text-blue-900 uppercase tracking-wider">
                    Mã phòng trọ (Invite code)
                  </label>
                  <div className="relative">
                    <KeyRound className="w-4 h-4 text-blue-400 absolute left-3 top-3.5" />
                    <input
                      type="text"
                      value={registerData.invite_code}
                      onChange={(e) => setRegisterData({ ...registerData, invite_code: e.target.value.toUpperCase() })}
                      placeholder="Mã mời từ chủ trọ (nếu có)"
                      className="w-full pl-9 pr-4 py-2 bg-white border border-blue-200 rounded-lg text-sm uppercase tracking-wider font-mono focus:outline-none focus:ring-2 focus:ring-brandblue-500"
                    />
                  </div>
                  <p className="text-[11px] text-blue-600">
                    Nếu có mã mời do chủ trọ cấp, nhập vào đây để tự động kết nối vào phòng trọ.
                  </p>
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full mt-3 py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-semibold rounded-xl shadow-md shadow-primary-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <span className="inline-block animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Đăng ký & Bắt đầu</span>
                  </>
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
