/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from 'react';
import { useToast } from '../context/ToastContext';
import { auth as authApi } from '../services/api';
import { Lock, Eye, EyeOff, KeyRound, CheckCircle2, AlertCircle, X, ShieldCheck } from 'lucide-react';

export default function ChangePasswordModal({ isOpen, onClose }) {
  const { toast } = useToast();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  if (!isOpen) return null;

  const hasConfirm = confirmPassword.length > 0;
  const isMatch = newPassword === confirmPassword;
  const isLengthValid = newPassword.length >= 6;
  const canSubmit = currentPassword.length > 0 && isLengthValid && isMatch && !submitting;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!isMatch) {
      setErrorMsg('Mật khẩu xác nhận không khớp với mật khẩu mới');
      return;
    }

    if (newPassword.length < 6) {
      setErrorMsg('Mật khẩu mới phải có tối thiểu 6 ký tự');
      return;
    }

    if (newPassword === currentPassword) {
      setErrorMsg('Mật khẩu mới không được trùng với mật khẩu hiện tại');
      return;
    }

    setSubmitting(true);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      toast.success('Đổi mật khẩu thành công!');
      handleClose();
    } catch (err) {
      const msg = err.message || 'Đổi mật khẩu không thành công. Vui lòng kiểm tra lại.';
      setErrorMsg(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setErrorMsg(null);
    onClose?.();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-3xl max-w-md w-full p-6 sm:p-7 space-y-5 shadow-2xl border border-slate-200 animate-scaleIn">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-primary-50 text-primary-600 flex items-center justify-center">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-black text-slate-900">
                Đổi mật khẩu tài khoản
              </h3>
              <p className="text-xs text-slate-500">
                Yêu cầu xác thực mật khẩu hiện tại để bảo mật
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error alert banner if any */}
        {errorMsg && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-2xl flex items-start gap-2.5 text-xs text-red-700 animate-fadeIn">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 font-medium leading-relaxed">{errorMsg}</div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4 text-left">
          {/* Mật khẩu hiện tại */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Mật khẩu hiện tại <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type={showCurrentPassword ? 'text' : 'password'}
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Nhập mật khẩu đang sử dụng"
                className="w-full min-h-[44px] pl-10 pr-12 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all text-slate-900"
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword((p) => !p)}
                className="absolute right-0 top-0 bottom-0 px-3.5 flex items-center justify-center min-w-[44px] text-slate-400 hover:text-slate-700 transition-colors"
                title={showCurrentPassword ? 'Ẩn' : 'Hiện'}
              >
                {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Mật khẩu mới */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Mật khẩu mới <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type={showNewPassword ? 'text' : 'password'}
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Tối thiểu 6 ký tự"
                className="w-full min-h-[44px] pl-10 pr-12 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all text-slate-900"
              />
              <button
                type="button"
                onClick={() => setShowNewPassword((p) => !p)}
                className="absolute right-0 top-0 bottom-0 px-3.5 flex items-center justify-center min-w-[44px] text-slate-400 hover:text-slate-700 transition-colors"
                title={showNewPassword ? 'Ẩn' : 'Hiện'}
              >
                {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {newPassword.length > 0 && newPassword.length < 6 && (
              <p className="mt-1 text-[11px] font-medium text-amber-600 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Mật khẩu phải có ít nhất 6 ký tự</span>
              </p>
            )}
          </div>

          {/* Xác nhận mật khẩu mới (Realtime Feedback) */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Nhập lại mật khẩu mới <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Nhập lại chính xác mật khẩu mới"
                className={`w-full min-h-[44px] pl-10 pr-12 py-2.5 rounded-xl text-sm transition-all focus:outline-none focus:ring-2 ${
                  !hasConfirm
                    ? 'bg-slate-50 border border-slate-200 focus:bg-white focus:ring-primary-500 text-slate-900'
                    : isMatch
                    ? 'bg-emerald-50/30 border border-emerald-400 focus:bg-white focus:ring-emerald-500 text-slate-900'
                    : 'bg-red-50/30 border border-red-400 focus:bg-white focus:ring-red-500 text-slate-900'
                }`}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword((p) => !p)}
                className="absolute right-0 top-0 bottom-0 px-3.5 flex items-center justify-center min-w-[44px] text-slate-400 hover:text-slate-700 transition-colors"
                title={showConfirmPassword ? 'Ẩn' : 'Hiện'}
              >
                {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {hasConfirm && (
              isMatch ? (
                <p className="mt-1 text-[11px] font-semibold text-emerald-600 flex items-center gap-1 animate-fadeIn">
                  <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>Mật khẩu mới trùng khớp</span>
                </p>
              ) : (
                <p className="mt-1 text-[11px] font-semibold text-red-600 flex items-center gap-1 animate-fadeIn">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>Mật khẩu nhập lại chưa khớp với mật khẩu mới</span>
                </p>
              )
            )}
          </div>

          {/* Action buttons */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              className="min-h-[44px] flex-1 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 active:scale-[0.98] text-slate-700 font-semibold text-xs sm:text-sm rounded-xl transition-all"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="min-h-[44px] flex-1 px-4 py-2.5 bg-primary-600 hover:bg-primary-700 active:scale-[0.98] text-white font-bold text-xs sm:text-sm rounded-xl shadow-md shadow-primary-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-1.5"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>{submitting ? 'Đang cập nhật...' : 'Đổi mật khẩu'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
