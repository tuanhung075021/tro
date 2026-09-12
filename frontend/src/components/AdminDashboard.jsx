/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { admin as adminApi } from '../services/api';
import {
  Scale,
  Users,
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  RotateCcw,
  KeyRound,
  Eye,
  EyeOff,
  Check,
  X,
  History,
  FileText,
  Info,
  Droplets,
  Zap,
  ArrowUpRight,
  UserCheck,
  UserX,
  UserMinus,
  Calendar,
  Phone,
  User,
  Lock,
  Unlock,
  Copy,
} from 'lucide-react';

export default function AdminDashboard() {
  const { user, isRootAdmin } = useAuth();
  const { toast } = useToast();

  const [activeTab, setActiveTab] = useState('tariff'); // 'tariff' | 'admins'

  // ============================================================================
  // TAB 1: Tariff State
  // ============================================================================
  const [tariff, setTariff] = useState(null);
  const [loadingTariff, setLoadingTariff] = useState(true);
  const [updatingTariff, setUpdatingTariff] = useState(false);
  const [tariffHistory, setTariffHistory] = useState([]);
  const [showResetModal, setShowResetModal] = useState(false);
  const [resettingTariff, setResettingTariff] = useState(false);
  const [snapshotModalData, setSnapshotModalData] = useState(null);

  // Editable form state for tariff
  const [tiers, setTiers] = useState([
    { tier_number: 1, tier_name: 'Bậc 1 (0 - 50 kWh)', min_kwh: 0, max_kwh: 50, max_threshold: 50, unit_price: 1984 },
    { tier_number: 2, tier_name: 'Bậc 2 (51 - 100 kWh)', min_kwh: 51, max_kwh: 100, max_threshold: 50, unit_price: 2050 },
    { tier_number: 3, tier_name: 'Bậc 3 (101 - 200 kWh)', min_kwh: 101, max_kwh: 200, max_threshold: 100, unit_price: 2380 },
    { tier_number: 4, tier_name: 'Bậc 4 (201 - 300 kWh)', min_kwh: 201, max_kwh: 300, max_threshold: 100, unit_price: 2998 },
    { tier_number: 5, tier_name: 'Bậc 5 (301 - 400 kWh)', min_kwh: 301, max_kwh: 400, max_threshold: 100, unit_price: 3350 },
    { tier_number: 6, tier_name: 'Bậc 6 (Từ 401 kWh trở lên)', min_kwh: 401, max_kwh: null, max_threshold: null, unit_price: 3460 },
  ]);
  const [vatRate, setVatRate] = useState(8);
  const [waterRate, setWaterRate] = useState(8500);
  const [tariffVersion, setTariffVersion] = useState('');
  const [tariffNote, setTariffNote] = useState('');

  // ============================================================================
  // TAB 2: Admin Management State
  // ============================================================================
  const [requests, setRequests] = useState([]);
  const [admins, setAdmins] = useState([]);
  const [loadingAdmins, setLoadingAdmins] = useState(false);

  // Modals for Tab 2
  const [rejectModal, setRejectModal] = useState({ open: false, requestId: null, username: '', reason: '' });
  const [newSecret, setNewSecret] = useState('');
  const [showSecret, setShowSecret] = useState(false);
  const [rotateAdminPassword, setRotateAdminPassword] = useState('');
  const [showRotateAdminPassword, setShowRotateAdminPassword] = useState(false);
  const [showRotateConfirm, setShowRotateConfirm] = useState(false);
  const [rotatingSecret, setRotatingSecret] = useState(false);

  // Secret Key Reveal State (Root Admin password authentication)
  const [activeSecret, setActiveSecret] = useState(null);
  const [showRevealModal, setShowRevealModal] = useState(false);
  const [revealPassword, setRevealPassword] = useState('');
  const [showRevealPassword, setShowRevealPassword] = useState(false);
  const [revealingSecret, setRevealingSecret] = useState(false);
  const [revealError, setRevealError] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);

  // ============================================================================
  // Load Tariff Data
  // ============================================================================
  const fetchTariffData = useCallback(async () => {
    setLoadingTariff(true);
    try {
      const [tariffRes, historyRes] = await Promise.all([
        adminApi.getTariff(),
        adminApi.getTariffHistory(),
      ]);

      setTariff(tariffRes);
      if (tariffRes.electricity_tiers && tariffRes.electricity_tiers.length === 6) {
        setTiers(
          tariffRes.electricity_tiers.map((t, idx) => ({
            tier_number: t.tier_number || idx + 1,
            tier_name: t.tier_name || `Bậc ${idx + 1}`,
            min_kwh: t.min_kwh,
            max_kwh: t.max_kwh,
            max_threshold: t.max_threshold,
            unit_price: t.unit_price,
          }))
        );
      }
      setVatRate(tariffRes.vat_rate > 1 ? tariffRes.vat_rate : Math.round(tariffRes.vat_rate * 100));
      setWaterRate(tariffRes.water_rate || 8500);
      setTariffVersion(tariffRes.tariff_version || 'QD-1279-2023');
      setTariffHistory(historyRes || []);
    } catch (err) {
      toast.error(err.message || 'Không thể tải biểu giá hệ thống');
    } finally {
      setLoadingTariff(false);
    }
  }, [toast]);

  // ============================================================================
  // Load Admin Data (Root Admin only)
  // ============================================================================
  const fetchAdminData = useCallback(async () => {
    if (!isRootAdmin) return;
    setLoadingAdmins(true);
    try {
      const [reqsRes, adminsRes] = await Promise.all([
        adminApi.getRequests(),
        adminApi.getAdmins(),
      ]);
      setRequests(reqsRes || []);
      setAdmins(adminsRes || []);
    } catch (err) {
      toast.error(err.message || 'Không thể tải dữ liệu quản trị viên');
    } finally {
      setLoadingAdmins(false);
    }
  }, [isRootAdmin, toast]);

  useEffect(() => {
    fetchTariffData();
  }, [fetchTariffData]);

  useEffect(() => {
    if (activeTab === 'admins' && isRootAdmin) {
      fetchAdminData();
    }
  }, [activeTab, isRootAdmin, fetchAdminData]);

  // ============================================================================
  // Monotonicity Validation for 6 Electricity Tiers
  // tier[i+1].unit_price > tier[i].unit_price
  // ============================================================================
  const monotonicityErrors = {};
  let hasMonotonicityViolation = false;

  for (let i = 0; i < tiers.length - 1; i++) {
    const currentPrice = Number(tiers[i].unit_price) || 0;
    const nextPrice = Number(tiers[i + 1].unit_price) || 0;
    if (nextPrice <= currentPrice) {
      monotonicityErrors[i + 1] = `Giá bậc ${i + 2} (${nextPrice.toLocaleString()} đ) phải lớn hơn bậc ${i + 1} (${currentPrice.toLocaleString()} đ)`;
      hasMonotonicityViolation = true;
    }
  }

  const handleTierPriceChange = (index, val) => {
    const num = val === '' ? '' : Math.max(0, Number(val));
    setTiers((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], unit_price: num };
      return copy;
    });
  };

  const handleUpdateTariff = async (e) => {
    e.preventDefault();
    if (hasMonotonicityViolation) {
      toast.error('Vui lòng điều chỉnh đơn giá để bậc sau luôn lớn hơn bậc trước');
      return;
    }

    setUpdatingTariff(true);
    try {
      const payload = {
        electricity_tiers: tiers.map((t) => ({
          tier_number: t.tier_number,
          tier_name: t.tier_name,
          min_kwh: t.min_kwh,
          max_kwh: t.max_kwh,
          max_threshold: t.max_threshold,
          unit_price: Number(t.unit_price),
        })),
        vat_rate: Number(vatRate) / 100,
        water_rate: Number(waterRate),
        tariff_version: tariffVersion.trim() || undefined,
        note: tariffNote.trim() || undefined,
      };

      const res = await adminApi.updateTariff(payload);
      setTariff(res);
      setTariffNote('');
      toast.success('Lưu biểu giá mới thành công!');
      // Reload history
      const historyRes = await adminApi.getTariffHistory();
      setTariffHistory(historyRes || []);
    } catch (err) {
      toast.error(err.message || 'Cập nhật biểu giá thất bại');
    } finally {
      setUpdatingTariff(false);
    }
  };

  const handleResetTariff = async () => {
    setResettingTariff(true);
    try {
      const res = await adminApi.resetTariff('QD-1279-2023');
      setTariff(res);
      if (res.electricity_tiers && res.electricity_tiers.length === 6) {
        setTiers(
          res.electricity_tiers.map((t, idx) => ({
            tier_number: t.tier_number || idx + 1,
            tier_name: t.tier_name || `Bậc ${idx + 1}`,
            min_kwh: t.min_kwh,
            max_kwh: t.max_kwh,
            max_threshold: t.max_threshold,
            unit_price: t.unit_price,
          }))
        );
      }
      setVatRate(res.vat_rate > 1 ? res.vat_rate : Math.round(res.vat_rate * 100));
      setWaterRate(res.water_rate || 8500);
      setTariffVersion(res.tariff_version || 'QD-1279-2023');
      setShowResetModal(false);
      toast.success('Đã khôi phục biểu giá chuẩn QĐ 1279/QĐ-BCT thành công!');
      const historyRes = await adminApi.getTariffHistory();
      setTariffHistory(historyRes || []);
    } catch (err) {
      toast.error(err.message || 'Khôi phục biểu giá thất bại');
    } finally {
      setResettingTariff(false);
    }
  };

  // ============================================================================
  // Tab 2 Action Handlers
  // ============================================================================
  const handleApprove = async (reqId, username) => {
    try {
      await adminApi.approveRequest(reqId);
      toast.success(`Đã phê duyệt tài khoản @${username} thành Quản trị viên!`);
      fetchAdminData();
    } catch (err) {
      toast.error(err.message || 'Phê duyệt thất bại');
    }
  };

  const handleConfirmReject = async () => {
    if (!rejectModal.requestId) return;
    try {
      await adminApi.rejectRequest(rejectModal.requestId, rejectModal.reason.trim());
      toast.info(`Đã từ chối yêu cầu của @${rejectModal.username}.`);
      setRejectModal({ open: false, requestId: null, username: '', reason: '' });
      fetchAdminData();
    } catch (err) {
      toast.error(err.message || 'Từ chối thất bại');
    }
  };

  const handlePromote = async (userId, username) => {
    try {
      await adminApi.promoteAdmin(userId);
      toast.success(`Đã nâng cấp @${username} thành Root Admin!`);
      fetchAdminData();
    } catch (err) {
      toast.error(err.message || 'Nâng quyền thất bại');
    }
  };

  const handleDemote = async (userId, username) => {
    try {
      await adminApi.demoteAdmin(userId);
      toast.info(`Đã hạ quyền @${username} xuống Quản trị viên.`);
      fetchAdminData();
    } catch (err) {
      // Backend returns 400 if demoting sole root admin
      toast.error(err.message || 'Không thể hạ quyền Root Admin duy nhất của hệ thống');
    }
  };

  const handleOpenRevealModal = () => {
    setRevealPassword('');
    setShowRevealPassword(false);
    setRevealError('');
    setShowRevealModal(true);
  };

  const handleConfirmReveal = async (e) => {
    if (e) e.preventDefault();
    if (!revealPassword) {
      setRevealError('Vui lòng nhập mật khẩu tài khoản Root Admin');
      return;
    }
    setRevealingSecret(true);
    setRevealError('');
    try {
      const res = await adminApi.revealSecret({ admin_password: revealPassword });
      setActiveSecret(res.active_secret_key);
      setShowRevealModal(false);
      setRevealPassword('');
      toast.success('Mở khóa xem Secret Key thành công!');
    } catch (err) {
      setRevealError(err.message || 'Mật khẩu quản trị viên không chính xác');
    } finally {
      setRevealingSecret(false);
    }
  };

  const handleCopySecret = async () => {
    if (!activeSecret) return;
    try {
      await navigator.clipboard.writeText(activeSecret);
      setCopiedSecret(true);
      toast.success('Đã sao chép Khóa Bí mật vào bộ nhớ tạm!');
      setTimeout(() => setCopiedSecret(false), 2500);
    } catch {
      toast.error('Không thể tự động sao chép, vui lòng copy thủ công');
    }
  };

  const handleRotateSecret = async () => {
    if (newSecret.trim().length < 8) {
      toast.error('Secret key mới phải có ít nhất 8 ký tự');
      return;
    }
    if (!rotateAdminPassword) {
      toast.error('Vui lòng nhập mật khẩu tài khoản Root Admin để xác thực');
      return;
    }
    setRotatingSecret(true);
    try {
      await adminApi.rotateSecret({
        new_secret: newSecret.trim(),
        admin_password: rotateAdminPassword,
      });
      toast.success('Xoay vòng Secret Key thành công!');
      setShowRotateConfirm(false);
      setNewSecret('');
      setRotateAdminPassword('');
      setActiveSecret(null);
      fetchAdminData();
    } catch (err) {
      toast.error(err.message || 'Xoay vòng Secret Key thất bại');
    } finally {
      setRotatingSecret(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Dashboard Header Banner */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-5 sm:p-7 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
              Bảng Quản trị Hệ thống tro.
            </h1>
            {isRootAdmin ? (
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-purple-100 text-purple-800 border border-purple-300 text-xs font-bold rounded-full">
                <ShieldAlert className="w-3.5 h-3.5 text-purple-700" />
                <span>Root Admin</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-indigo-100 text-indigo-800 border border-indigo-300 text-xs font-bold rounded-full">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-700" />
                <span>Quản trị viên</span>
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-500">
            Quản lý biểu giá điện nước nhà nước tập trung và phân quyền quản trị viên
          </p>
        </div>

        {/* Tab Navigation Pill Buttons */}
        <div className="flex items-center gap-1.5 p-1.5 bg-slate-100 rounded-2xl self-start md:self-auto">
          <button
            onClick={() => setActiveTab('tariff')}
            className={`min-h-[40px] px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition-all ${
              activeTab === 'tariff'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Scale className="w-4 h-4 text-primary-600" />
            <span>Biểu giá nhà nước</span>
          </button>

          {isRootAdmin && (
            <button
              onClick={() => setActiveTab('admins')}
              className={`min-h-[40px] px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition-all ${
                activeTab === 'admins'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Users className="w-4 h-4 text-purple-600" />
              <span>Quản lý Quản trị viên</span>
              {requests.length > 0 && (
                <span className="px-1.5 py-0.5 bg-amber-500 text-white rounded-full text-[10px] font-bold">
                  {requests.length}
                </span>
              )}
            </button>
          )}
        </div>
      </div>

      {/* ==================================================================== */}
      {/* TAB 1: BIỂU GIÁ NHÀ NƯỚC                                             */}
      {/* ==================================================================== */}
      {activeTab === 'tariff' && (
        <div className="space-y-6">
          {/* Active Version Info Card */}
          <div className="bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-white rounded-3xl border border-blue-200/80 p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
            <div className="space-y-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-blue-700 block">
                Phiên bản Biểu giá Đang Áp Dụng
              </span>
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="text-xl sm:text-2xl font-black font-mono text-slate-900">
                  {tariff?.tariff_version || 'QD-1279-2023'}
                </span>
                <span className="px-2.5 py-0.5 bg-emerald-100 text-emerald-800 text-xs font-bold rounded-full border border-emerald-300">
                  Hoạt động
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Lần cập nhật cuối:{' '}
                <strong className="text-slate-700">{formatDate(tariff?.tariff_updated_at)}</strong>
              </p>
            </div>

            <button
              onClick={() => setShowResetModal(true)}
              className="min-h-[44px] inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs sm:text-sm rounded-xl border border-slate-300 shadow-sm transition-all active:scale-[0.98] self-start sm:self-auto"
              title="Khôi phục về biểu giá chuẩn QĐ 1279"
            >
              <RotateCcw className="w-4 h-4 text-amber-600" />
              <span>Khôi phục chuẩn QĐ 1279</span>
            </button>
          </div>

          {/* Form Cập nhật Biểu giá */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-5 sm:p-7 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                  <Zap className="w-5 h-5 fill-current" />
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900">
                    Cập nhật Biểu giá Bán lẻ Điện sinh hoạt (6 Bậc)
                  </h2>
                  <p className="text-xs text-slate-500">
                    Quy định đơn giá lũy tiến từng bậc theo Quyết định Bộ Công Thương
                  </p>
                </div>
              </div>
            </div>

            <form onSubmit={handleUpdateTariff} className="space-y-6">
              {/* Monotonicity Warning Banner if violated */}
              {hasMonotonicityViolation && (
                <div className="p-4 rounded-2xl bg-red-50 border border-red-200 flex items-start gap-3 animate-headShake">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div className="text-xs text-red-800 space-y-1">
                    <p className="font-bold">Quy tắc lũy tiến bậc thang không hợp lệ!</p>
                    <p>
                      Đơn giá bậc sau bắt buộc phải lớn hơn bậc liền trước. Vui lòng kiểm tra lại các bậc được đánh dấu màu đỏ dưới đây trước khi lưu.
                    </p>
                  </div>
                </div>
              )}

              {/* 6 Tiers Grid / List */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {tiers.map((tier, idx) => {
                  const isInvalid = Boolean(monotonicityErrors[idx]);
                  return (
                    <div
                      key={tier.tier_number}
                      className={`p-4 rounded-2xl border transition-all ${
                        isInvalid
                          ? 'border-red-400 bg-red-50/50 shadow-sm'
                          : 'border-slate-200 bg-slate-50/50 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold text-xs sm:text-sm text-slate-900">
                          {tier.tier_name}
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 bg-white border border-slate-200 rounded-md text-slate-600">
                          Bậc {tier.tier_number}
                        </span>
                      </div>

                      <div className="space-y-1.5">
                        <label className="block text-[11px] text-slate-500 font-medium">
                          Đơn giá trước thuế (VNĐ/kWh)
                        </label>
                        <div className="relative">
                          <input
                            type="number"
                            min="0"
                            step="1"
                            value={tier.unit_price}
                            onChange={(e) => handleTierPriceChange(idx, e.target.value)}
                            required
                            className={`w-full min-h-[44px] px-3 py-2 text-sm font-mono font-bold rounded-xl border transition-colors ${
                              isInvalid
                                ? 'border-red-500 bg-white text-red-900 focus:ring-2 focus:ring-red-400'
                                : 'border-slate-300 bg-white text-slate-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-100'
                            }`}
                          />
                          <span className="absolute right-3 top-3 text-xs text-slate-400">đ</span>
                        </div>

                        {isInvalid && (
                          <p className="text-[11px] text-red-600 font-semibold flex items-center gap-1 mt-1">
                            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                            <span>{monotonicityErrors[idx]}</span>
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* General Settings: VAT, Water, Version, Note */}
              <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-4">
                <h3 className="text-xs sm:text-sm font-bold text-slate-800">
                  Thông số Thuế, Nước sinh hoạt & Ghi chú Phiên bản
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs text-slate-600 font-medium mb-1">
                      Thuế suất VAT Điện (%)
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={vatRate}
                        onChange={(e) => setVatRate(e.target.value)}
                        required
                        className="w-full min-h-[44px] px-3 py-2 text-sm font-mono font-bold rounded-xl border border-slate-300 bg-white text-slate-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
                      />
                      <span className="absolute right-3 top-3 text-xs text-slate-400">%</span>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1 block">Mặc định 8%</span>
                  </div>

                  <div>
                    <label className="block text-xs text-slate-600 font-medium mb-1">
                      Đơn giá Nước sạch (đ/m³)
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        min="0"
                        step="100"
                        value={waterRate}
                        onChange={(e) => setWaterRate(e.target.value)}
                        required
                        className="w-full min-h-[44px] px-3 py-2 text-sm font-mono font-bold rounded-xl border border-slate-300 bg-white text-slate-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
                      />
                      <span className="absolute right-3 top-3 text-xs text-slate-400">đ/m³</span>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1 block">Mặc định 8.500 đ</span>
                  </div>

                  <div>
                    <label className="block text-xs text-slate-600 font-medium mb-1">
                      Mã Phiên bản Mới
                    </label>
                    <input
                      type="text"
                      placeholder="VD: QD-1279-MOD-2026"
                      value={tariffVersion}
                      onChange={(e) => setTariffVersion(e.target.value)}
                      className="w-full min-h-[44px] px-3 py-2 text-sm font-mono font-bold rounded-xl border border-slate-300 bg-white text-slate-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
                    />
                    <span className="text-[10px] text-slate-400 mt-1 block">Để trống tự sinh</span>
                  </div>

                  <div>
                    <label className="block text-xs text-slate-600 font-medium mb-1">
                      Ghi chú Thay đổi
                    </label>
                    <input
                      type="text"
                      placeholder="Căn cứ pháp lý điều chỉnh..."
                      value={tariffNote}
                      onChange={(e) => setTariffNote(e.target.value)}
                      className="w-full min-h-[44px] px-3 py-2 text-sm rounded-xl border border-slate-300 bg-white text-slate-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
                    />
                    <span className="text-[10px] text-slate-400 mt-1 block">Lưu vào ChangeLog</span>
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={hasMonotonicityViolation || updatingTariff}
                  className="min-h-[44px] w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 bg-primary-600 hover:bg-primary-700 active:scale-[0.98] text-white font-bold text-xs sm:text-sm rounded-xl shadow-md shadow-primary-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <CheckCircle2 className={`w-4 h-4 ${updatingTariff ? 'animate-spin' : ''}`} />
                  <span>{updatingTariff ? 'Đang lưu...' : 'Lưu biểu giá mới'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Lịch sử Thay đổi Biểu giá (TariffChangeLog History) */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-5 sm:p-7 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center">
                  <History className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm sm:text-base font-bold text-slate-900">
                    Nhật ký Thay đổi Biểu giá (Tariff Change Log)
                  </h3>
                  <p className="text-xs text-slate-500">Lịch sử các lần điều chỉnh biểu giá nhà nước</p>
                </div>
              </div>

              <button
                onClick={fetchTariffData}
                className="min-h-[40px] px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Làm mới</span>
              </button>
            </div>

            {tariffHistory.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
                Chưa có nhật ký điều chỉnh nào. Biểu giá đang giữ nguyên theo cấu hình khởi tạo ban đầu.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-slate-200 scrollbar-thin">
                <table className="w-full text-left text-xs min-w-[640px]">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                    <tr>
                      <th className="py-3 px-4">Thời điểm</th>
                      <th className="py-3 px-4">Phiên bản</th>
                      <th className="py-3 px-4">Người thực hiện</th>
                      <th className="py-3 px-4">Ghi chú</th>
                      <th className="py-3 px-4 text-right">Chi tiết</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {tariffHistory.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/60 transition-colors">
                        <td className="py-3 px-4 font-mono text-slate-700 whitespace-nowrap">
                          {formatDate(item.changed_at)}
                        </td>
                        <td className="py-3 px-4 font-bold text-slate-900 font-mono whitespace-nowrap">
                          {item.tariff_version}
                        </td>
                        <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                          @{item.changed_by_username || `ID ${item.changed_by_id}`}
                        </td>
                        <td className="py-3 px-4 text-slate-500 max-w-xs truncate">
                          {item.note || 'Điều chỉnh định kỳ'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => setSnapshotModalData(item)}
                            className="min-h-[36px] px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg text-xs inline-flex items-center gap-1 transition-colors"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            <span>Snapshot</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* TAB 2: QUẢN LÝ QUẢN TRỊ VIÊN (ROOT ADMIN ONLY)                       */}
      {/* ==================================================================== */}
      {activeTab === 'admins' && isRootAdmin && (
        <div className="space-y-6">
          {/* Hàng đợi Phê duyệt Admin (Pending Queue) */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-5 sm:p-7 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900">
                    Hàng đợi Xét duyệt Quản trị viên
                  </h2>
                  <p className="text-xs text-slate-500">
                    Danh sách người dùng đăng ký kích hoạt quyền admin đang chờ phê duyệt
                  </p>
                </div>
              </div>

              <span className="px-2.5 py-1 bg-amber-100 text-amber-800 text-xs font-bold rounded-full border border-amber-300">
                {requests.length} yêu cầu
              </span>
            </div>

            {requests.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400 bg-slate-50 rounded-2xl border border-dashed border-slate-200 space-y-1">
                <CheckCircle2 className="w-6 h-6 text-slate-300 mx-auto" />
                <p className="font-semibold text-slate-600">Không có yêu cầu nào đang chờ xét duyệt</p>
                <p>Tất cả các đơn đăng ký Quản trị viên đã được xử lý.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {requests.map((req) => (
                  <div
                    key={req.id}
                    className="p-4 rounded-2xl border border-amber-200 bg-amber-50/30 flex flex-col justify-between gap-4 shadow-sm"
                  >
                    <div className="space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h4 className="font-black text-sm text-slate-900">
                            {req.full_name || req.username}
                          </h4>
                          <span className="text-xs font-mono text-slate-500">@{req.username}</span>
                        </div>
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded-full border border-amber-300">
                          Chờ duyệt
                        </span>
                      </div>

                      <div className="text-xs text-slate-600 space-y-1 bg-white/80 p-2.5 rounded-xl border border-slate-100">
                        <div className="flex items-center gap-1.5">
                          <Phone className="w-3.5 h-3.5 text-slate-400" />
                          <span>{req.phone || 'Chưa cung cấp SĐT'}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          <span>Thời điểm: {formatDate(req.requested_at)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-1 border-t border-amber-200/60">
                      <button
                        onClick={() => handleApprove(req.id, req.username)}
                        className="min-h-[40px] flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98] text-white font-bold text-xs rounded-xl shadow-sm transition-all"
                        title="Phê duyệt quyền Quản trị viên"
                      >
                        <Check className="w-4 h-4" />
                        <span>Duyệt</span>
                      </button>

                      <button
                        onClick={() =>
                          setRejectModal({
                            open: true,
                            requestId: req.id,
                            username: req.username,
                            reason: '',
                          })
                        }
                        className="min-h-[40px] inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-white hover:bg-red-50 hover:text-red-600 text-slate-700 font-semibold text-xs rounded-xl border border-slate-200 transition-all active:scale-[0.98]"
                        title="Từ chối yêu cầu"
                      >
                        <X className="w-4 h-4" />
                        <span>Từ chối</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Danh sách Quản trị viên Hiện tại (Active Admins List) */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-5 sm:p-7 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900">
                    Danh sách Quản trị viên Hệ thống
                  </h2>
                  <p className="text-xs text-slate-500">
                    Phân quyền Root Admin và Quản trị viên tiêu chuẩn
                  </p>
                </div>
              </div>

              <button
                onClick={fetchAdminData}
                className="min-h-[40px] px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Làm mới</span>
              </button>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-slate-200 scrollbar-thin">
              <table className="w-full text-left text-xs min-w-[600px]">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                  <tr>
                    <th className="py-3 px-4">Tài khoản</th>
                    <th className="py-3 px-4">Họ và tên</th>
                    <th className="py-3 px-4">Vai trò</th>
                    <th className="py-3 px-4">Ngày tạo</th>
                    <th className="py-3 px-4 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {admins.map((adm) => {
                    const isSelf = adm.id === user?.id;
                    const isAdmRoot = adm.role === 'root_admin';
                    return (
                      <tr key={adm.id} className="hover:bg-slate-50/60 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-slate-900 whitespace-nowrap">
                          @{adm.username}
                          {isSelf && (
                            <span className="ml-1.5 text-[10px] text-primary-600 font-normal">
                              (bạn)
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-700 whitespace-nowrap">
                          {adm.full_name || '—'}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          {isAdmRoot ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-purple-100 text-purple-800 font-bold rounded-full border border-purple-200 text-[11px]">
                              <ShieldAlert className="w-3 h-3 text-purple-600" />
                              <span>Root Admin</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-indigo-100 text-indigo-800 font-bold rounded-full border border-indigo-200 text-[11px]">
                              <ShieldCheck className="w-3 h-3 text-indigo-600" />
                              <span>Quản trị viên</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                          {formatDate(adm.created_at)}
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          {isAdmRoot ? (
                            <button
                              onClick={() => handleDemote(adm.id, adm.username)}
                              disabled={isSelf && admins.filter((a) => a.role === 'root_admin').length <= 1}
                              className="min-h-[36px] px-3 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 font-bold rounded-lg text-xs inline-flex items-center gap-1 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                              title="Hạ quyền xuống Quản trị viên"
                            >
                              <UserMinus className="w-3.5 h-3.5" />
                              <span>Hạ quyền</span>
                            </button>
                          ) : (
                            <button
                              onClick={() => handlePromote(adm.id, adm.username)}
                              className="min-h-[36px] px-3 py-1 bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-300 font-bold rounded-lg text-xs inline-flex items-center gap-1 transition-colors"
                              title="Nâng cấp lên Root Admin"
                            >
                              <ArrowUpRight className="w-3.5 h-3.5" />
                              <span>Nâng cấp Root</span>
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Khối Khóa Bí mật Quản trị Hiện tại (Current Active Secret Key) */}
          <div className="bg-white rounded-3xl border border-amber-200/90 shadow-sm p-5 sm:p-7 space-y-4">
            <div className="flex items-center justify-between border-b border-amber-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                  <KeyRound className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900">
                    Khóa Bí mật Quản trị Hiện tại (Active Secret Key)
                  </h2>
                  <p className="text-xs text-slate-500">
                    Dùng cho cú pháp kích hoạt Easter Egg Admin: <code className="text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded font-mono font-semibold">username::secret_key</code>
                  </p>
                </div>
              </div>
              <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${
                activeSecret
                  ? 'bg-amber-100 text-amber-800 border-amber-300'
                  : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}>
                {activeSecret ? 'Đang mở khóa' : 'Đã khóa bảo vệ'}
              </span>
            </div>

            {activeSecret ? (
              <div className="p-4 rounded-2xl bg-amber-50/90 border border-amber-300 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-amber-900 mb-1 flex items-center gap-1.5">
                      <Unlock className="w-3.5 h-3.5 text-amber-600" />
                      <span>Chuỗi Secret Key đang hoạt động:</span>
                    </div>
                    <div className="font-mono text-base font-black text-amber-950 bg-white/90 px-3.5 py-2 rounded-xl border border-amber-200 shadow-inner select-all break-all">
                      {activeSecret}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      type="button"
                      onClick={handleCopySecret}
                      className="min-h-[40px] px-3.5 py-2 bg-amber-600 hover:bg-amber-700 active:scale-95 text-white font-bold text-xs rounded-xl inline-flex items-center gap-1.5 shadow-sm transition-all"
                      title="Sao chép vào bộ nhớ tạm"
                    >
                      {copiedSecret ? <Check className="w-4 h-4 text-white" /> : <Copy className="w-4 h-4" />}
                      <span>{copiedSecret ? 'Đã sao chép!' : 'Sao chép'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveSecret(null)}
                      className="min-h-[40px] px-3.5 py-2 bg-slate-200 hover:bg-slate-300 active:scale-95 text-slate-700 font-bold text-xs rounded-xl inline-flex items-center gap-1.5 transition-all"
                      title="Ẩn khóa bí mật"
                    >
                      <EyeOff className="w-4 h-4" />
                      <span>Ẩn lại</span>
                    </button>
                  </div>
                </div>
                <p className="text-[11px] text-amber-800 leading-relaxed">
                  Lưu ý: Không chia sẻ khóa này công khai. Khi muốn tạo tài khoản Admin mới, hãy cung cấp cú pháp trên kèm khóa này cho ứng viên tin cậy.
                </p>
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-2xl bg-slate-50 border border-slate-200">
                <div className="space-y-1">
                  <div className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-slate-500" />
                    <span>Trạng thái bảo vệ:</span>
                  </div>
                  <div className="font-mono text-sm tracking-widest text-slate-400 font-bold">
                    ••••••••••••••••••••
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Khóa được mã hóa bằng thuật toán đối xứng an toàn. Cần xác thực mật khẩu Root Admin để giải mã xem nội dung.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleOpenRevealModal}
                  className="min-h-[44px] px-4 py-2 bg-slate-900 hover:bg-slate-800 active:scale-95 text-white font-bold text-xs sm:text-sm rounded-xl inline-flex items-center justify-center gap-2 shadow-sm transition-all flex-shrink-0"
                >
                  <Lock className="w-4 h-4 text-amber-400" />
                  <span>Mở khóa xem Key</span>
                </button>
              </div>
            )}
          </div>

          {/* Khối Xoay vòng Secret Key (Secret Key Rotation) */}
          <div className="bg-white rounded-3xl border border-red-200/90 shadow-sm p-5 sm:p-7 space-y-4">
            <div className="flex items-center gap-2.5 border-b border-red-100 pb-3">
              <div className="w-9 h-9 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base sm:text-lg font-bold text-slate-900">
                  Xoay vòng Khóa Bí mật Quản trị (Secret Key Rotation)
                </h2>
                <p className="text-xs text-slate-500">
                  Cập nhật secret key dùng cho cú pháp kích hoạt Easter Egg Admin
                </p>
              </div>
            </div>

            {/* Warning Box */}
            <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-amber-900 space-y-1">
                <p className="font-bold">CẢNH BÁO BẢO MẬT QUAN TRỌNG:</p>
                <p className="leading-relaxed">
                  Khi thực hiện xoay vòng khóa mới, khóa bí mật hiện tại sẽ ngay lập tức bị vô hiệu hóa. 
                  Toàn bộ các yêu cầu xét duyệt đang chờ trong hàng đợi từ khóa cũ sẽ tự động bị hủy bỏ.
                </p>
              </div>
            </div>

            <div className="max-w-md space-y-3 pt-1">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Nhập Secret Key Mới (Tối thiểu 8 ký tự)
                </label>
                <div className="relative">
                  <input
                    type={showSecret ? 'text' : 'password'}
                    placeholder="Ví dụ: OHTLP_TRO.2026_V2"
                    value={newSecret}
                    onChange={(e) => setNewSecret(e.target.value)}
                    className="w-full min-h-[44px] px-3.5 pr-10 py-2 text-sm font-mono rounded-xl border border-slate-300 bg-white text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-100"
                  />
                  <button
                    type="button"
                    onClick={() => setShowSecret((p) => !p)}
                    className="absolute right-2.5 top-2.5 p-1 text-slate-400 hover:text-slate-700"
                    title={showSecret ? 'Ẩn' : 'Hiện'}
                  >
                    {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {newSecret.length > 0 && newSecret.length < 8 && (
                  <p className="text-[11px] text-red-600 font-semibold flex items-center gap-1 mt-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Khóa bí mật phải có độ dài tối thiểu 8 ký tự</span>
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Mật khẩu tài khoản Root Admin của bạn (@{user?.username})
                </label>
                <div className="relative">
                  <input
                    type={showRotateAdminPassword ? 'text' : 'password'}
                    placeholder="Nhập mật khẩu để xác thực xoay key..."
                    value={rotateAdminPassword}
                    onChange={(e) => setRotateAdminPassword(e.target.value)}
                    className="w-full min-h-[44px] px-3.5 pr-10 py-2 text-sm rounded-xl border border-slate-300 bg-white text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-100"
                  />
                  <button
                    type="button"
                    onClick={() => setShowRotateAdminPassword((p) => !p)}
                    className="absolute right-2.5 top-2.5 p-1 text-slate-400 hover:text-slate-700"
                    title={showRotateAdminPassword ? 'Ẩn' : 'Hiện'}
                  >
                    {showRotateAdminPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Yêu cầu mật khẩu của chính bạn để đảm bảo không bị thao tác ngoài ý muốn.
                </p>
              </div>

              <button
                type="button"
                disabled={newSecret.trim().length < 8 || !rotateAdminPassword}
                onClick={() => setShowRotateConfirm(true)}
                className="min-h-[44px] w-full inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-red-600 hover:bg-red-700 active:scale-[0.98] text-white font-bold text-xs sm:text-sm rounded-xl shadow-md shadow-red-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <KeyRound className="w-4 h-4" />
                <span>Thực hiện xoay vòng Key</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* MODAL: Xác thực Root Admin để xem Secret Key                        */}
      {/* ==================================================================== */}
      {showRevealModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-scaleIn">
            <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto">
              <Lock className="w-6 h-6" />
            </div>

            <div className="text-center space-y-1">
              <h3 className="text-base sm:text-lg font-black text-slate-900">
                Xác thực danh tính Root Admin
              </h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Vui lòng nhập mật khẩu tài khoản Root Admin của bạn để giải mã và hiển thị Khóa Bí mật Quản trị hiện tại.
              </p>
            </div>

            <form onSubmit={handleConfirmReveal} className="space-y-4">
              <div className="space-y-1.5 text-left">
                <label className="block text-xs font-semibold text-slate-700">
                  Mật khẩu tài khoản (@{user?.username})
                </label>
                <div className="relative">
                  <input
                    type={showRevealPassword ? 'text' : 'password'}
                    placeholder="Nhập mật khẩu đăng nhập..."
                    value={revealPassword}
                    onChange={(e) => {
                      setRevealPassword(e.target.value);
                      if (revealError) setRevealError('');
                    }}
                    autoFocus
                    required
                    className="w-full min-h-[44px] px-3.5 pr-10 py-2 text-sm rounded-xl border border-slate-300 bg-white text-slate-900 focus:border-amber-500 focus:ring-2 focus:ring-amber-100"
                  />
                  <button
                    type="button"
                    onClick={() => setShowRevealPassword((p) => !p)}
                    className="absolute right-2.5 top-2.5 p-1 text-slate-400 hover:text-slate-700"
                    title={showRevealPassword ? 'Ẩn' : 'Hiện'}
                  >
                    {showRevealPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {revealError && (
                  <p className="text-xs text-red-600 font-semibold flex items-center gap-1 mt-1">
                    <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>{revealError}</span>
                  </p>
                )}
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowRevealModal(false);
                    setRevealPassword('');
                    setRevealError('');
                  }}
                  className="min-h-[44px] flex-1 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs sm:text-sm rounded-xl"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={revealingSecret || !revealPassword}
                  className="min-h-[44px] flex-1 px-4 py-2 bg-amber-600 hover:bg-amber-700 active:scale-95 text-white font-bold text-xs sm:text-sm rounded-xl shadow-md shadow-amber-500/20 disabled:opacity-50"
                >
                  {revealingSecret ? 'Đang giải mã...' : 'Xác nhận mở khóa'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* MODAL: Xác nhận Reset Chuẩn QĐ 1279                                 */}
      {/* ==================================================================== */}
      {showResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-scaleIn">
            <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto">
              <RotateCcw className="w-6 h-6" />
            </div>

            <div className="text-center space-y-2">
              <h3 className="text-base sm:text-lg font-black text-slate-900">
                Khôi phục Biểu giá chuẩn QĐ 1279?
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Hành động này sẽ thiết lập lại toàn bộ đơn giá 6 bậc điện và nước về mức chuẩn ban hành theo Quyết định 1279/QĐ-BCT (Bậc 1: 1.984 đ, Bậc 6: 3.460 đ, Nước: 8.500 đ/m³, VAT: 8%).
              </p>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowResetModal(false)}
                className="min-h-[44px] flex-1 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs sm:text-sm rounded-xl"
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                onClick={handleResetTariff}
                disabled={resettingTariff}
                className="min-h-[44px] flex-1 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs sm:text-sm rounded-xl shadow-md shadow-amber-500/20 disabled:opacity-60"
              >
                {resettingTariff ? 'Đang khôi phục...' : 'Xác nhận khôi phục'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* MODAL: Nhập Lý do Từ chối Admin                                      */}
      {/* ==================================================================== */}
      {rejectModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-scaleIn">
            <div className="w-12 h-12 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center mx-auto">
              <X className="w-6 h-6" />
            </div>

            <div className="text-center space-y-1">
              <h3 className="text-base sm:text-lg font-black text-slate-900">
                Từ chối yêu cầu Quản trị viên
              </h3>
              <p className="text-xs text-slate-500">
                Từ chối cấp quyền cho tài khoản <strong>@{rejectModal.username}</strong>
              </p>
            </div>

            <div className="space-y-1.5 text-left">
              <label className="block text-xs font-semibold text-slate-700">
                Lý do từ chối (Tùy chọn)
              </label>
              <textarea
                rows={3}
                placeholder="Nhập lý do từ chối để lưu vào hồ sơ kiểm toán..."
                value={rejectModal.reason}
                onChange={(e) => setRejectModal((p) => ({ ...p, reason: e.target.value }))}
                className="w-full p-3 text-xs rounded-xl border border-slate-300 bg-white text-slate-900 focus:border-red-500 focus:ring-2 focus:ring-red-100"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setRejectModal({ open: false, requestId: null, username: '', reason: '' })}
                className="min-h-[44px] flex-1 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs sm:text-sm rounded-xl"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleConfirmReject}
                className="min-h-[44px] flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold text-xs sm:text-sm rounded-xl shadow-md shadow-red-500/20"
              >
                Xác nhận từ chối
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* MODAL: Xác nhận Xoay vòng Key                                       */}
      {/* ==================================================================== */}
      {showRotateConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-red-200 animate-scaleIn">
            <div className="w-12 h-12 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="text-center space-y-2">
              <h3 className="text-base sm:text-lg font-black text-slate-900">
                Xác nhận Xoay vòng Secret Key?
              </h3>
              <p className="text-xs text-red-700 leading-relaxed bg-red-50 p-3 rounded-2xl border border-red-200">
                Khóa bí mật cũ sẽ hết hiệu lực ngay lập tức. Toàn bộ các yêu cầu chờ xét duyệt admin hiện có sẽ tự động bị hủy bỏ!
              </p>
              <div className="bg-slate-50 p-3 rounded-2xl border border-slate-200 text-left text-xs space-y-1">
                <div className="text-slate-500 font-medium">Khóa mới sẽ thiết lập:</div>
                <div className="font-mono font-bold text-slate-800 break-all select-all">{newSecret}</div>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowRotateConfirm(false)}
                className="min-h-[44px] flex-1 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs sm:text-sm rounded-xl"
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                onClick={handleRotateSecret}
                disabled={rotatingSecret}
                className="min-h-[44px] flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold text-xs sm:text-sm rounded-xl shadow-md shadow-red-500/20 disabled:opacity-60"
              >
                {rotatingSecret ? 'Đang xoay vòng...' : 'Đồng ý & Xoay Key'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* MODAL: Xem Chi tiết Snapshot JSON                                    */}
      {/* ==================================================================== */}
      {snapshotModalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-scaleIn">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Snapshot Biểu giá: {snapshotModalData.tariff_version}
                </h3>
              </div>
              <button
                onClick={() => setSnapshotModalData(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between text-slate-500">
                <span>Thời điểm: {formatDate(snapshotModalData.changed_at)}</span>
                <span>Người sửa: @{snapshotModalData.changed_by_username || snapshotModalData.changed_by_id}</span>
              </div>
              <pre className="p-3 bg-slate-900 text-emerald-400 font-mono text-[11px] rounded-2xl overflow-x-auto max-h-60 scrollbar-thin">
                {(() => {
                  try {
                    return JSON.stringify(JSON.parse(snapshotModalData.snapshot_json), null, 2);
                  } catch {
                    return snapshotModalData.snapshot_json;
                  }
                })()}
              </pre>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setSnapshotModalData(null)}
                className="min-h-[40px] px-5 py-2 bg-slate-800 hover:bg-slate-900 text-white font-bold text-xs rounded-xl"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
