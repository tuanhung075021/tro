/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { rooms as roomApi } from '../services/api';
import {
  Building2,
  Home,
  FileText,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Calendar,
  Zap,
  Droplets,
  ExternalLink,
  Check,
  Copy,
  Users,
  Phone,
  User,
  MapPin,
  Plus,
  KeyRound,
  RefreshCw,
  Printer,
} from 'lucide-react';

export default function TenantDashboard({ onViewPublicInvoice }) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [myRooms, setMyRooms] = useState([]);
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [invoicesList, setInvoicesList] = useState([]);
  const [loadingRooms, setLoadingRooms] = useState(true);
  const [loadingInvoices, setLoadingInvoices] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [copiedToken, setCopiedToken] = useState(null);

  // Modals & form state
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [inviteCodeInput, setInviteCodeInput] = useState('');
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState(null);

  // Fetch invoices for a given room
  const fetchInvoices = useCallback(async (roomId) => {
    if (!roomId) {
      setInvoicesList([]);
      return;
    }
    setLoadingInvoices(true);
    try {
      const invs = await roomApi.getInvoices(roomId);
      // Tenants only see published invoices; drafts are hidden until published by landlord
      const published = (invs || []).filter((i) => i.status === 'published');
      setInvoicesList(published);
    } catch (err) {
      console.error('Error fetching invoices:', err);
      setInvoicesList([]);
    } finally {
      setLoadingInvoices(false);
    }
  }, []);

  // Fetch rooms assigned to this tenant
  const fetchMyRooms = useCallback(async () => {
    setLoadingRooms(true);
    setError(null);
    try {
      const roomsData = await roomApi.getMyRooms();
      const rooms = roomsData || [];
      setMyRooms(rooms);

      if (rooms.length > 0) {
        // Keep current room if still valid, otherwise pick first
        setSelectedRoom((prev) => {
          const match = prev ? rooms.find((r) => r.id === prev.id) : null;
          const current = match || rooms[0];
          fetchInvoices(current.id);
          return current;
        });
      } else {
        setSelectedRoom(null);
        setInvoicesList([]);
      }
    } catch (err) {
      setError(err.message || 'Không thể tải thông tin phòng trọ.');
      setMyRooms([]);
      setSelectedRoom(null);
      setInvoicesList([]);
    } finally {
      setLoadingRooms(false);
    }
  }, [fetchInvoices]);

  useEffect(() => {
    fetchMyRooms();
  }, [fetchMyRooms]);

  const handleSelectRoom = (room) => {
    setSelectedRoom(room);
    fetchInvoices(room.id);
  };

  const handleJoinRoom = async (e) => {
    e.preventDefault();
    const cleanCode = inviteCodeInput.trim().toUpperCase();
    if (!cleanCode) {
      setJoinError('Vui lòng nhập mã mời phòng.');
      return;
    }
    setJoining(true);
    setJoinError(null);
    try {
      const joined = await roomApi.join({ invite_code: cleanCode });
      toast.success(`Đã tham gia Phòng ${joined.room_number} thành công!`);
      setInviteCodeInput('');
      setShowJoinModal(false);
      await fetchMyRooms();
    } catch (err) {
      setJoinError(err.message || 'Mã mời phòng không hợp lệ hoặc phòng đã có người thuê.');
    } finally {
      setJoining(false);
    }
  };

  const handleCopy = (text, key) => {
    navigator.clipboard?.writeText(text);
    setCopiedToken(key);
    toast.success('Đã sao chép vào bộ nhớ tạm!');
    setTimeout(() => setCopiedToken(null), 2500);
  };

  return (
    <div className="space-y-8">
      {/* Clean SaaS Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Phòng trọ của tôi
          </h1>
          <p className="text-slate-500 text-xs sm:text-sm mt-1">
            Theo dõi chi tiết phòng ở, định mức và đối chiếu minh bạch các hóa đơn điện nước
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {myRooms.length > 0 && (
            <button
              onClick={() => {
                setJoinError(null);
                setInviteCodeInput('');
                setShowJoinModal(true);
              }}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-primary-700 bg-primary-50 hover:bg-primary-100 border border-primary-200 rounded-xl transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Tham gia phòng khác</span>
            </button>
          )}

          <button
            onClick={fetchMyRooms}
            title="Làm mới"
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Global Alerts */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-2xl text-sm text-red-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700 font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-sm text-emerald-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Check className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-500 hover:text-emerald-700 font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {/* Main Content Area */}
      {loadingRooms ? (
        <div className="p-12 text-center text-slate-400 text-sm bg-white rounded-3xl border border-slate-200">
          Đang tải dữ liệu phòng trọ của bạn...
        </div>
      ) : myRooms.length === 0 ? (
        /* Empty State: Tenant not assigned to any room */
        <div className="bg-white rounded-3xl border border-slate-200 p-8 sm:p-12 text-center max-w-xl mx-auto shadow-sm space-y-6">
          <div className="w-16 h-16 rounded-3xl bg-primary-50 border border-primary-100 flex items-center justify-center text-primary-600 mx-auto shadow-inner">
            <Home className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-bold text-slate-900">
              Bạn chưa được gán vào phòng trọ nào
            </h2>
            <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
              Chủ trọ có thể gán trực tiếp tài khoản của bạn thông qua Username{' '}
              <strong className="text-slate-800">@{user?.username}</strong>
              {user?.phone ? (
                <> hoặc Số điện thoại <strong className="text-slate-800">{user.phone}</strong></>
              ) : null}.
            </p>
          </div>

          {/* Direct Invite Code Input Form */}
          <div className="pt-4 border-t border-slate-100">
            <p className="text-xs font-semibold text-slate-700 mb-3 text-left">
              Hoặc nhập Mã mời phòng do chủ trọ cung cấp:
            </p>

            {joinError && (
              <div className="p-3 mb-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 text-left">
                {joinError}
              </div>
            )}

            <form onSubmit={handleJoinRoom} className="flex flex-col sm:flex-row items-center gap-2">
              <div className="relative w-full">
                <KeyRound className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  required
                  value={inviteCodeInput}
                  onChange={(e) => setInviteCodeInput(e.target.value.toUpperCase())}
                  placeholder="Ví dụ: AB3K9X1Z"
                  className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono text-slate-900 uppercase tracking-wider focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <button
                type="submit"
                disabled={joining}
                className="w-full sm:w-auto px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all whitespace-nowrap disabled:opacity-50"
              >
                {joining ? 'Đang kết nối...' : 'Tham gia phòng'}
              </button>
            </form>
          </div>
        </div>
      ) : (
        /* Room Assigned: Display Property & Room Card + Invoices */
        <div className="space-y-6">
          {/* Room Selector if multiple rooms */}
          {myRooms.length > 1 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
              <span className="text-xs text-slate-400 font-semibold mr-1">Phòng của bạn:</span>
              {myRooms.map((r) => {
                const active = selectedRoom?.id === r.id;
                return (
                  <button
                    key={r.id}
                    onClick={() => handleSelectRoom(r)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
                      active
                        ? 'bg-primary-600 text-white shadow-sm'
                        : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                    }`}
                  >
                    Phòng {r.room_number} {r.property_name ? `• ${r.property_name}` : ''}
                  </button>
                );
              })}
            </div>
          )}

          {/* Active Room Overview Card */}
          {selectedRoom && (
            <div className="bg-white rounded-3xl border border-slate-200/80 p-6 sm:p-7 shadow-sm">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                {/* Left: Property & Room Identity */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2.5">
                    <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-xs font-bold rounded-full border border-emerald-200">
                      Đang thuê
                    </span>
                    <span className="text-xs text-slate-400">
                      Mã định danh: #{selectedRoom.id}
                    </span>
                  </div>

                  <div>
                    <h2 className="text-2xl sm:text-3xl font-black text-slate-900">
                      Phòng {selectedRoom.room_number}
                    </h2>
                    <p className="text-sm font-semibold text-slate-700 mt-1 flex items-center gap-1.5">
                      <Building2 className="w-4 h-4 text-primary-600" />
                      <span>{selectedRoom.property_name || 'Khu trọ'}</span>
                    </p>
                    {selectedRoom.property_address && (
                      <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" />
                        <span>{selectedRoom.property_address}</span>
                      </p>
                    )}
                  </div>
                </div>

                {/* Right: Landlord & Quota Details */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  {/* Quota */}
                  <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1">
                    <div className="flex items-center gap-1.5 text-slate-500">
                      <Users className="w-3.5 h-3.5 text-primary-600" />
                      <span className="font-semibold">Định mức sử dụng:</span>
                    </div>
                    <p className="text-base font-black text-slate-900">
                      {selectedRoom.current_people_count} người
                    </p>
                    <p className="text-[11px] text-slate-400">Dùng tính bậc thang lũy tiến</p>
                  </div>

                  {/* Landlord Contact */}
                  <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1">
                    <div className="flex items-center gap-1.5 text-slate-500">
                      <User className="w-3.5 h-3.5 text-emerald-600" />
                      <span className="font-semibold">Chủ nhà trọ:</span>
                    </div>
                    <p className="text-sm font-bold text-slate-900">
                      {selectedRoom.landlord_name || 'Chủ trọ'}
                    </p>
                    <p className="text-[11px] text-slate-500 flex items-center gap-1">
                      <Phone className="w-3 h-3 text-slate-400" />
                      <span>{selectedRoom.landlord_phone || 'Chưa cập nhật SĐT'}</span>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Invoices List */}
          <div className="bg-white rounded-3xl border border-slate-200/80 p-6 sm:p-8 space-y-6 shadow-sm">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary-600" />
                  <span>Bảng kê hóa đơn & Đối chiếu tiền thu</span>
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Kiểm tra chi phí điện nước và số tiền chênh lệch theo quy định bậc thang nhà nước
                </p>
              </div>
            </div>

            {loadingInvoices ? (
              <div className="p-8 text-center text-slate-400 text-sm">
                Đang tải danh sách hóa đơn...
              </div>
            ) : invoicesList.length === 0 ? (
              <div className="p-10 border-2 border-dashed border-slate-200 rounded-2xl text-center">
                <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-700">Phòng này chưa có hóa đơn nào</p>
                <p className="text-xs text-slate-400 mt-1">
                  Khi chủ trọ chốt số công tơ điện nước hàng tháng, bảng kê minh bạch sẽ tự động hiển thị tại đây.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {invoicesList.map((inv) => {
                  const isOvercharged = inv.diff_amount > 0;
                  return (
                    <div
                      key={inv.id}
                      className={`p-5 rounded-2xl border transition-all ${
                        isOvercharged
                          ? 'border-red-200 bg-red-50/30 hover:bg-red-50/50'
                          : 'border-slate-200 bg-slate-50/40 hover:bg-slate-50/80'
                      }`}
                    >
                      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                        {/* Month & Overcharge Status */}
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Calendar className="w-4 h-4 text-slate-500" />
                            <span className="text-base font-black text-slate-900">
                              Tháng {inv.month_year}
                            </span>
                            {inv.short_code && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-mono font-bold rounded-lg bg-primary-50 text-primary-700 border border-primary-200">
                                {inv.short_code}
                              </span>
                            )}

                            {isOvercharged ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold rounded-full bg-red-100 text-red-700 border border-red-300">
                                <ShieldAlert className="w-3.5 h-3.5" />
                                <span>Thu lố {Number(inv.diff_amount).toLocaleString('vi-VN')} đ</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                                <ShieldCheck className="w-3.5 h-3.5" />
                                <span>Chuẩn quy định</span>
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-500">
                            Mã hóa đơn #{inv.id} {inv.short_code ? `• Mã tra cứu: ${inv.short_code}` : ''} • Chốt ngày{' '}
                            {inv.created_at ? new Date(inv.created_at).toLocaleDateString('vi-VN') : 'Gần đây'}
                          </p>
                        </div>

                        {/* Breakdown Numbers */}
                        <div className="flex flex-wrap items-center gap-3 text-xs">
                          {/* Điện */}
                          <div className="px-3 py-1.5 bg-white rounded-xl border border-slate-200">
                            <span className="text-slate-400 block text-[10px]">Điện ({inv.elec_kwh} kWh)</span>
                            <span className="font-bold text-slate-800">
                              {Number(inv.elec_amount).toLocaleString('vi-VN')} đ
                            </span>
                          </div>

                          {/* Nước */}
                          <div className="px-3 py-1.5 bg-white rounded-xl border border-slate-200">
                            <span className="text-slate-400 block text-[10px]">Nước ({inv.water_usage} m³)</span>
                            <span className="font-bold text-slate-800">
                              {Number(inv.water_amount).toLocaleString('vi-VN')} đ
                            </span>
                          </div>

                          {/* Tổng luật định */}
                          <div className="px-3 py-1.5 bg-emerald-50 rounded-xl border border-emerald-200">
                            <span className="text-emerald-700 block text-[10px] font-bold">Tổng quy định</span>
                            <span className="font-black text-emerald-900">
                              {Number(inv.total_statutory_amount).toLocaleString('vi-VN')} đ
                            </span>
                          </div>

                          {/* Tiền thực thu */}
                          <div className="px-3 py-1.5 bg-slate-100 rounded-xl border border-slate-200">
                            <span className="text-slate-500 block text-[10px]">Tiền thực thu</span>
                            <span className="font-black text-slate-900">
                              {Number(inv.actual_collected_amount).toLocaleString('vi-VN')} đ
                            </span>
                          </div>

                          {/* Action Buttons */}
                          <div className="flex items-center gap-2">
                            {inv.short_code && (
                              <button
                                onClick={() => handleCopy(inv.short_code, `sc-${inv.id}`)}
                                className="flex items-center gap-1 px-2.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-all"
                                title="Sao chép mã tra cứu"
                              >
                                {copiedToken === `sc-${inv.id}` ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                                <span>{copiedToken === `sc-${inv.id}` ? 'Đã chép' : 'Mã'}</span>
                              </button>
                            )}

                            {inv.share_token && (
                              <button
                                onClick={() => onViewPublicInvoice?.(inv.share_token)}
                                className="flex items-center gap-1 px-3 py-2 bg-white hover:bg-slate-100 text-slate-800 text-xs font-semibold rounded-xl border border-slate-200 shadow-sm transition-all"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                                <span>Chi tiết & In</span>
                              </button>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Overcharged brief notice */}
                      {isOvercharged && (
                        <div className="mt-3 pt-2.5 border-t border-red-200 text-xs text-red-800 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
                          <span>
                            Số tiền thực thu cao hơn giá định mức nhà nước <strong>{Number(inv.diff_amount).toLocaleString('vi-VN')} đ</strong>.
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL: Tham gia phòng khác */}
      {showJoinModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border border-slate-200">
            <h3 className="text-xl font-bold text-slate-900 mb-2">Tham gia phòng trọ mới</h3>
            <p className="text-xs text-slate-500 mb-4">
              Nhập mã mời phòng do chủ trọ cung cấp để liên kết tài khoản của bạn vào phòng.
            </p>

            {joinError && (
              <div className="p-3 mb-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                {joinError}
              </div>
            )}

            <form onSubmit={handleJoinRoom} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase">
                  Mã mời phòng (Invite Code) *
                </label>
                <input
                  type="text"
                  required
                  value={inviteCodeInput}
                  onChange={(e) => setInviteCodeInput(e.target.value.toUpperCase())}
                  placeholder="Ví dụ: AB3K9X1Z"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono uppercase tracking-wider text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowJoinModal(false);
                    setJoinError(null);
                  }}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={joining}
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-bold text-xs rounded-xl shadow-sm disabled:opacity-50"
                >
                  {joining ? 'Đang kết nối...' : 'Xác nhận tham gia'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
