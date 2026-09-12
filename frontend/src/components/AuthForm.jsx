/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useEffect, useCallback } from 'react';
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
  Eye,
  EyeOff,
  RefreshCw,
  X,
} from 'lucide-react';

export default function AuthForm({ initialTab = 'login', onAuthSuccess, onClose }) {
  const { login, register, authError } = useAuth();
  const [tab, setTab] = useState(initialTab); // 'login' | 'register'
  const [role, setRole] = useState('landlord'); // 'landlord' | 'tenant'
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  // Password visibility toggles
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Math Captcha state (100% Pure FOSS)
  const [captchaNum1, setCaptchaNum1] = useState(5);
  const [captchaNum2, setCaptchaNum2] = useState(7);
  const [captchaAnswer, setCaptchaAnswer] = useState('');

  const generateNewCaptcha = useCallback(() => {
    const n1 = Math.floor(Math.random() * 9) + 2;
    const n2 = Math.floor(Math.random() * 9) + 1;
    setCaptchaNum1(n1);
    setCaptchaNum2(n2);
    setCaptchaAnswer('');
  }, []);

  useEffect(() => {
    generateNewCaptcha();
  }, [generateNewCaptcha]);

  // Form states
  const [loginData, setLoginData] = useState({ username: '', password: '' });
  const [registerData, setRegisterData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
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

    // 1. Validate Confirm Password match
    if (registerData.password !== registerData.confirmPassword) {
      setFormError('Mật khẩu nhập lại không khớp. Vui lòng kiểm tra lại.');
      return;
    }

    // 2. Validate Pure FOSS Math Captcha
    const expected = captchaNum1 + captchaNum2;
    if (parseInt(captchaAnswer.trim(), 10) !== expected) {
      setFormError(`Câu trả lời bảo mật không chính xác. Hãy tính lại: ${captchaNum1} + ${captchaNum2} = ?`);
      generateNewCaptcha();
      return;
    }

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
      generateNewCaptcha();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="relative bg-white rounded-3xl shadow-2xl border border-slate-200/90 overflow-hidden">
        {/* Optional close button */}
        {onClose && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 z-20 w-8 h-8 rounded-full bg-black/20 hover:bg-black/30 text-white flex items-center justify-center transition-colors"
            title="Đóng"
          >
            <X className="w-5 h-5" />
          </button>
        )}

        {/* Header decoration */}
        <div className="bg-gradient-to-r from-primary-600 via-emerald-600 to-teal-700 px-6 py-7 text-white text-center">
          <div className="inline-flex items-center justify-center w-11 h-11 rounded-xl bg-white/10 backdrop-blur border border-white/20 mb-2 shadow-inner">
            <Zap className="w-6 h-6 text-primary-200 fill-current" />
          </div>
          <h2 className="text-2xl font-black tracking-tight">tro.</h2>
          <p className="text-emerald-100 text-xs mt-0.5">
            Hệ thống Quản lý Lưu trú & Đối chiếu Chi phí Điện Nước Minh bạch
          </p>
        </div>

        <div className="p-6 sm:p-8">
          {/* Error display */}
          {(formError || authError) && (
            <div className="mb-5 p-3.5 bg-red-50 border border-red-200 rounded-2xl text-xs sm:text-sm text-red-700 flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="leading-snug">{formError || authError}</div>
            </div>
          )}

          {/* LOGIN FORM (DEFAULT) */}
          {tab === 'login' && (
            <div className="space-y-5">
              <div className="text-center pb-1">
                <h3 className="text-lg font-black text-slate-900">Đăng nhập tài khoản</h3>
                <p className="text-xs text-slate-500 mt-0.5">Truy cập để quản lý và theo dõi hóa đơn</p>
              </div>

              <form onSubmit={handleLoginSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                    Tên đăng nhập
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                    <input
                      type="text"
                      required
                      value={loginData.username}
                      onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                      placeholder="Nhập tên tài khoản"
                      className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                    Mật khẩu
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                    <input
                      type={showLoginPassword ? 'text' : 'password'}
                      required
                      value={loginData.password}
                      onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                      placeholder="Nhập mật khẩu"
                      className="w-full pl-10 pr-11 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowLoginPassword((prev) => !prev)}
                      className="absolute right-3 top-3 text-slate-400 hover:text-slate-700 transition-colors p-0.5"
                      title={showLoginPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                    >
                      {showLoginPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full mt-2 py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-bold text-sm rounded-xl shadow-md shadow-primary-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <span className="inline-block animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  ) : (
                    <>
                      <span>Đăng nhập</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>

              {/* Facebook-style navigation footer */}
              <div className="pt-4 border-t border-slate-100 text-center text-xs text-slate-600">
                <span>Bạn chưa có tài khoản? </span>
                <button
                  type="button"
                  onClick={() => {
                    setTab('register');
                    setFormError(null);
                  }}
                  className="text-primary-600 hover:text-primary-700 font-bold hover:underline transition-colors"
                >
                  Đăng ký
                </button>
              </div>
            </div>
          )}

          {/* REGISTER FORM */}
          {tab === 'register' && (
            <div className="space-y-4">
              <div className="text-center pb-1">
                <h3 className="text-lg font-black text-slate-900">Tạo tài khoản mới</h3>
                <p className="text-xs text-slate-500 mt-0.5">Tham gia cộng đồng nhà trọ minh bạch</p>
              </div>

              <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
                {/* Role Selection */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                    Vai trò của bạn:
                  </label>
                  <div className="grid grid-cols-2 gap-2.5">
                    <button
                      type="button"
                      onClick={() => setRole('landlord')}
                      className={`p-2.5 rounded-xl border flex flex-col items-center gap-1 transition-all text-xs font-bold ${
                        role === 'landlord'
                          ? 'border-primary-600 bg-primary-50 text-primary-900 ring-2 ring-primary-500/20 shadow-sm'
                          : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <Building2 className={`w-4 h-4 ${role === 'landlord' ? 'text-primary-600' : 'text-slate-400'}`} />
                      <span>Chủ nhà trọ</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setRole('tenant')}
                      className={`p-2.5 rounded-xl border flex flex-col items-center gap-1 transition-all text-xs font-bold ${
                        role === 'tenant'
                          ? 'border-teal-600 bg-teal-50 text-teal-900 ring-2 ring-teal-500/20 shadow-sm'
                          : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <UserCheck className={`w-4 h-4 ${role === 'tenant' ? 'text-teal-600' : 'text-slate-400'}`} />
                      <span>Người thuê trọ</span>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Họ và tên
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                    <input
                      type="text"
                      required
                      value={registerData.full_name}
                      onChange={(e) => setRegisterData({ ...registerData, full_name: e.target.value })}
                      placeholder="Nguyễn Văn A"
                      className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Tên đăng nhập
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                    <input
                      type="text"
                      required
                      value={registerData.username}
                      onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })}
                      placeholder="nguyenvana"
                      className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
                    />
                  </div>
                </div>

                {/* Password field with Eye toggle */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Mật khẩu
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                    <input
                      type={showRegPassword ? 'text' : 'password'}
                      required
                      value={registerData.password}
                      onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                      placeholder="Tối thiểu 6 ký tự"
                      className="w-full pl-10 pr-10 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowRegPassword((prev) => !prev)}
                      className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-700 transition-colors"
                      title={showRegPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                    >
                      {showRegPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Confirm Password field with Eye toggle */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Nhập lại mật khẩu
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      required
                      value={registerData.confirmPassword}
                      onChange={(e) => setRegisterData({ ...registerData, confirmPassword: e.target.value })}
                      placeholder="Xác nhận lại mật khẩu"
                      className="w-full pl-10 pr-10 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword((prev) => !prev)}
                      className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-700 transition-colors"
                      title={showConfirmPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                    >
                      {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Số điện thoại (tuỳ chọn)
                  </label>
                  <div className="relative">
                    <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                    <input
                      type="tel"
                      value={registerData.phone}
                      onChange={(e) => setRegisterData({ ...registerData, phone: e.target.value })}
                      placeholder="0912345678"
                      className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
                    />
                  </div>
                </div>

                {/* Invite code for tenant */}
                {role === 'tenant' && (
                  <div className="p-3 bg-teal-50/70 border border-teal-200 rounded-xl space-y-1">
                    <label className="block text-xs font-bold text-teal-900 uppercase tracking-wider">
                      Mã phòng trọ (Invite code)
                    </label>
                    <div className="relative">
                      <KeyRound className="w-4 h-4 text-teal-500 absolute left-3 top-2.5" />
                      <input
                        type="text"
                        value={registerData.invite_code}
                        onChange={(e) => setRegisterData({ ...registerData, invite_code: e.target.value.toUpperCase() })}
                        placeholder="Mã mời từ chủ trọ (nếu có)"
                        className="w-full pl-9 pr-4 py-1.5 bg-white border border-teal-200 rounded-lg text-xs uppercase tracking-wider font-mono focus:outline-none focus:ring-2 focus:ring-teal-500"
                      />
                    </div>
                  </div>
                )}

                {/* Pure FOSS Math Captcha to prevent spam bot */}
                <div className="p-3 bg-amber-50/80 border border-amber-200 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold text-amber-900">
                    <span>Xác thực chống Spam Bot (FOSS):</span>
                    <button
                      type="button"
                      onClick={generateNewCaptcha}
                      className="text-amber-700 hover:text-amber-950 flex items-center gap-1 font-semibold text-[11px]"
                      title="Đổi câu hỏi khác"
                    >
                      <RefreshCw className="w-3 h-3" />
                      <span>Đổi số khác</span>
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1.5 bg-white border border-amber-300 rounded-lg font-mono font-bold text-slate-800 text-sm shadow-sm select-none">
                      {captchaNum1} + {captchaNum2} = ?
                    </span>
                    <input
                      type="number"
                      required
                      value={captchaAnswer}
                      onChange={(e) => setCaptchaAnswer(e.target.value)}
                      placeholder="Nhập kết quả"
                      className="flex-1 px-3 py-1.5 bg-white border border-amber-300 rounded-lg text-sm font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full mt-2 py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-bold text-sm rounded-xl shadow-md shadow-primary-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
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

              {/* Facebook-style navigation footer */}
              <div className="pt-3 border-t border-slate-100 text-center text-xs text-slate-600">
                <span>Bạn đã có tài khoản? </span>
                <button
                  type="button"
                  onClick={() => {
                    setTab('login');
                    setFormError(null);
                  }}
                  className="text-primary-600 hover:text-primary-700 font-bold hover:underline transition-colors"
                >
                  Đăng nhập
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
