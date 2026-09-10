/*
 * Copyright (c) 2026 tro Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { rooms as roomApi, invoices as invoiceApi } from '../services/api';
import {
  UserCheck,
  Home,
  FileText,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Calendar,
  Zap,
  Droplets,
  ArrowRight,
  ExternalLink,
  Search,
  Check,
  Copy,
} from 'lucide-react';

export default function TenantDashboard({ onViewPublicInvoice }) {
  const { user } = useAuth();
  const [roomIdInput, setRoomIdInput] = useState(() => localStorage.getItem('tro_tenant_room_id') || '');
  const [activeRoomId, setActiveRoomId] = useState(() => {
    const saved = localStorage.getItem('tro_tenant_room_id');
    return saved ? parseInt(saved, 10) : null;
  });
  const [roomData, setRoomData] = useState(null);
  const [invoicesList, setInvoicesList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copiedToken, setCopiedToken] = useState(null);

  // Fetch room and invoices
  const loadRoomInfo = useCallback(async (roomId) => {
    if (!roomId) return;
    setLoading(true);
    setError(null);
    try {
      const room = await roomApi.get(roomId);
      setRoomData(room);
      setActiveRoomId(room.id);
      localStorage.setItem('tro_tenant_room_id', String(room.id));

      const invs = await roomApi.getInvoices(roomId);
      setInvoicesList(invs || []);
    } catch (err) {
      setError(err.message || 'Không tìm thấy phòng trọ hoặc bạn không có quyền truy cập');
      setRoomData(null);
      setInvoicesList([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-load saved room on mount
  useEffect(() => {
    const saved = localStorage.getItem('tro_tenant_room_id');
    if (saved) {
      const parsedId = parseInt(saved, 10);
      if (parsedId && !roomData) {
        loadRoomInfo(parsedId);
      }
    }
  }, [loadRoomInfo, roomData]);

  const handleSearchRoom = (e) => {
    e.preventDefault();
    const id = parseInt(roomIdInput.trim(), 10);
    if (!id) {
      setError('Vui lòng nhập ID phòng hợp lệ (số nguyên)');
      return;
    }
    loadRoomInfo(id);
  };

  const handleClearRoom = () => {
    localStorage.removeItem('tro_tenant_room_id');
    setActiveRoomId(null);
    setRoomData(null);
    setInvoicesList([]);
    setRoomIdInput('');
  };

  const handleCopy = (text, key) => {
    navigator.clipboard?.writeText(text);
    setCopiedToken(key);
    setTimeout(() => setCopiedToken(null), 2500);
  };

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-brandblue-950 to-slate-900 text-white p-6 sm:p-8 rounded-3xl shadow-xl border border-slate-700/50">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-brandblue-400 text-xs font-bold uppercase tracking-wider mb-2">
              <UserCheck className="w-4 h-4" />
              <span>Cổng Thông Tin Người Thuê Trọ</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight">
              Chào mừng, {user?.full_name || user?.username}!
            </h1>
            <p className="text-slate-300 text-sm mt-1.5 max-w-2xl leading-relaxed">
              Theo dõi đối chiếu cước phí điện nước theo bậc thang quy định nhà nước (Nghị quyết 204/2025/QH15 & Quyết định 1279/QĐ-BCT).
            </p>
          </div>

          {/* Quick Room Lookup input */}
          <form onSubmit={handleSearchRoom} className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="number"
                value={roomIdInput}
                onChange={(e) => setRoomIdInput(e.target.value)}
                placeholder="Nhập ID phòng của bạn"
                className="pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-xs sm:text-sm text-white focus:outline-none focus:ring-2 focus:ring-brandblue-500 w-44 sm:w-52"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-brandblue-600 hover:bg-brandblue-500 text-white font-semibold text-xs sm:text-sm rounded-xl transition-all"
            >
              Tra cứu
            </button>
          </form>
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

      {/* Room summary card if loaded */}
      {roomData && (
        <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-brandblue-50 border border-brandblue-100 flex items-center justify-center text-brandblue-600 font-black text-base">
                #{roomData.id}
              </div>
              <div>
                <h3 className="text-xl font-black text-slate-900">Phòng {roomData.room_number}</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Đang đăng ký định mức cho: <strong className="text-slate-800">{roomData.current_people_count} người</strong>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs font-semibold">
              <span className="px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full border border-emerald-200">
                {roomData.status === 'active' ? 'Đang kích hoạt' : 'Trống'}
              </span>
              <button
                onClick={handleClearRoom}
                className="px-3 py-1 text-slate-500 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-full transition-colors"
                title="Chọn hoặc nhập phòng khác"
              >
                Đổi phòng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Invoices List & Dispute Auditor */}
      <div className="bg-white rounded-3xl border border-slate-200/80 p-6 sm:p-8 space-y-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-brandblue-600" />
              <span>Lịch sử Hóa đơn & Đối chiếu Thu lố</span>
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Kiểm tra trực quan số tiền chênh lệch giữa giá thu thực tế và định mức luật định.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Đang tải hóa đơn...</div>
        ) : !activeRoomId ? (
          <div className="p-10 border-2 border-dashed border-slate-200 rounded-2xl text-center">
            <Search className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700">Chưa chọn phòng trọ</p>
            <p className="text-xs text-slate-400 mt-1">
              Vui lòng nhập ID phòng ở góc trên để xem chi tiết hóa đơn điện nước.
            </p>
          </div>
        ) : invoicesList.length === 0 ? (
          <div className="p-10 border-2 border-dashed border-slate-200 rounded-2xl text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700">Phòng này chưa có hóa đơn nào</p>
            <p className="text-xs text-slate-400 mt-1">
              Khi chủ trọ chốt số điện nước, hóa đơn minh bạch sẽ xuất hiện tại đây.
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
                      ? 'border-overcharge-300 bg-overcharge-50/40 hover:bg-overcharge-50/70'
                      : 'border-slate-200 bg-slate-50/40 hover:bg-slate-50/80'
                  }`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    {/* Month & Overcharge Status */}
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-slate-500" />
                        <span className="text-base font-black text-slate-900">
                          Tháng {inv.month_year}
                        </span>

                        {isOvercharged ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold rounded-full bg-overcharge-100 text-overcharge-700 border border-overcharge-300">
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
                        Mã hóa đơn #{inv.id} — Tạo ngày {inv.created_at ? new Date(inv.created_at).toLocaleDateString('vi-VN') : 'Mới'}
                      </p>
                    </div>

                    {/* Breakdown Numbers */}
                    <div className="flex flex-wrap items-center gap-4 text-xs">
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
                        <span className="text-emerald-700 block text-[10px] font-bold">Tổng luật định</span>
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
                    </div>

                    {/* View Button */}
                    <div className="flex items-center gap-2">
                      {inv.share_token && (
                        <button
                          onClick={() => onViewPublicInvoice?.(inv.share_token)}
                          className="flex items-center gap-1 px-3 py-2 bg-white hover:bg-slate-100 text-slate-800 text-xs font-semibold rounded-xl border border-slate-200 shadow-sm transition-all"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Chi tiết minh bạch</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Warning banner if overcharged */}
                  {isOvercharged && (
                    <div className="mt-3 pt-3 border-t border-overcharge-200 text-xs text-overcharge-800 flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-overcharge-600 flex-shrink-0 mt-0.5" />
                      <div>
                        Chủ trọ đã thu chênh lệch <strong>{Number(inv.diff_amount).toLocaleString('vi-VN')} đ</strong> so với biểu giá bậc thang nhà nước ban hành theo Thông tư 60/2025/TT-BCT và Nghị định 104/2022/NĐ-CP.
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
