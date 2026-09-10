/*
 * Copyright (c) 2026 tro Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useEffect, useCallback } from 'react';
import { properties as propApi, rooms as roomApi, auth as authApi } from '../services/api';
import {
  Building2,
  Plus,
  Home,
  Users,
  Copy,
  Check,
  Calculator,
  UserX,
  FileText,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';

export default function LandlordDashboard({ onViewPublicInvoice }) {
  const [propertiesList, setPropertiesList] = useState([]);
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [roomsList, setRoomsList] = useState([]);
  const [loadingProps, setLoadingProps] = useState(true);
  const [loadingRooms, setLoadingRooms] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Modals / sub-views
  const [showAddPropModal, setShowAddPropModal] = useState(false);
  const [showAddRoomModal, setShowAddRoomModal] = useState(false);
  const [calcModalRoom, setCalcModalRoom] = useState(null);
  const [copiedToken, setCopiedToken] = useState(null);

  // Forms
  const [propForm, setPropForm] = useState({ name: '', address: '' });
  const [roomForm, setRoomForm] = useState({ room_number: '', current_people_count: 1 });
  const [calcForm, setCalcForm] = useState({
    month_year: `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`,
    elec_start: '',
    elec_end: '',
    water_start: '',
    water_end: '',
    elec_method: 'TIERED',
    water_pricing_type: 'PER_M3',
    actual_collected_amount: '',
  });
  const [calcResult, setCalcResult] = useState(null);
  const [calculating, setCalculating] = useState(false);

  // Load properties
  const fetchProperties = useCallback(async () => {
    setLoadingProps(true);
    setError(null);
    try {
      const data = await propApi.list();
      setPropertiesList(data || []);
      if (data && data.length > 0 && !selectedProperty) {
        setSelectedProperty(data[0]);
      }
    } catch (err) {
      setError(err.message || 'Không thể tải danh sách khu trọ');
    } finally {
      setLoadingProps(false);
    }
  }, [selectedProperty]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  // Load rooms for selected property
  const fetchRooms = useCallback(async (propertyId) => {
    if (!propertyId) return;
    setLoadingRooms(true);
    try {
      const data = await propApi.getRooms(propertyId);
      setRoomsList(data || []);
    } catch (err) {
      setError(err.message || 'Không thể tải danh sách phòng');
    } finally {
      setLoadingRooms(false);
    }
  }, []);

  useEffect(() => {
    if (selectedProperty?.id) {
      fetchRooms(selectedProperty.id);
    }
  }, [selectedProperty, fetchRooms]);

  // Handlers
  const handleCreateProperty = async (e) => {
    e.preventDefault();
    if (!propForm.name.trim()) return;
    try {
      const created = await propApi.create({
        name: propForm.name.trim(),
        address: propForm.address.trim() || undefined,
      });
      setPropForm({ name: '', address: '' });
      setShowAddPropModal(false);
      setPropertiesList((prev) => [...prev, created]);
      setSelectedProperty(created);
      setSuccessMsg(`Đã thêm khu trọ "${created.name}"`);
    } catch (err) {
      setError(err.message || 'Không thể tạo khu trọ');
    }
  };

  const handleCreateRoom = async (e) => {
    e.preventDefault();
    if (!selectedProperty?.id || !roomForm.room_number.trim()) return;
    try {
      const created = await propApi.createRoom(selectedProperty.id, {
        room_number: roomForm.room_number.trim(),
        current_people_count: Number(roomForm.current_people_count) || 1,
      });
      setRoomForm({ room_number: '', current_people_count: 1 });
      setShowAddRoomModal(false);
      setRoomsList((prev) => [...prev, created]);
      setSuccessMsg(`Đã tạo phòng ${created.room_number}`);
    } catch (err) {
      setError(err.message || 'Không thể tạo phòng mới');
    }
  };

  const handleRemoveTenant = async (roomId, roomNumber) => {
    if (!window.confirm(`Xác nhận trả phòng cho Phòng ${roomNumber}? Mã mời phòng sẽ được cấp mới.`)) {
      return;
    }
    try {
      const updated = await authApi.removeTenant(roomId);
      setRoomsList((prev) => prev.map((r) => (r.id === roomId ? updated : r)));
      setSuccessMsg(`Đã đặt lại trạng thái phòng ${roomNumber} sang TRỐNG`);
    } catch (err) {
      setError(err.message || 'Không thể xóa khách thuê');
    }
  };

  const handleCopy = (text, key) => {
    navigator.clipboard?.writeText(text);
    setCopiedToken(key);
    setTimeout(() => setCopiedToken(null), 2500);
  };

  const handleCalculateInvoice = async (e) => {
    e.preventDefault();
    if (!calcModalRoom) return;
    setCalculating(true);
    setError(null);
    setCalcResult(null);
    try {
      const elecStart = parseFloat(calcForm.elec_start);
      const elecEnd = parseFloat(calcForm.elec_end);
      const waterStart = parseFloat(calcForm.water_start);
      const waterEnd = parseFloat(calcForm.water_end);

      if (isNaN(elecStart) || isNaN(elecEnd)) {
        throw new Error('Vui lòng nhập chỉ số điện đầu và cuối hợp lệ.');
      }
      if (isNaN(waterStart) || isNaN(waterEnd)) {
        throw new Error('Vui lòng nhập chỉ số nước đầu và cuối hợp lệ.');
      }

      const isTier3 = calcForm.elec_method === 'TIER3';
      const actualCollected =
        calcForm.actual_collected_amount !== '' &&
        !isNaN(parseFloat(calcForm.actual_collected_amount))
          ? parseFloat(calcForm.actual_collected_amount)
          : undefined;

      const payload = {
        month_year: calcForm.month_year.trim(),
        elec_start: elecStart,
        elec_end: elecEnd,
        water_start: waterStart,
        water_end: waterEnd,
        use_tier3: isTier3,
        has_registered_quota: !isTier3,
        people_count: Number(calcModalRoom.current_people_count) || 1,
        actual_collected_amount: actualCollected,
      };

      const result = await roomApi.calculateInvoice(calcModalRoom.id, payload);
      setCalcResult(result);
      setSuccessMsg(`Tính toán hóa đơn phòng ${calcModalRoom.room_number} thành công!`);
    } catch (err) {
      setError(err.message || 'Lỗi khi tính toán hóa đơn');
    } finally {
      setCalculating(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Banner Stats */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-primary-950 text-white p-6 sm:p-8 rounded-3xl shadow-xl border border-slate-700/50">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-primary-400 text-xs font-bold uppercase tracking-wider mb-2">
              <Building2 className="w-4 h-4" />
              <span>Bảng Quản Trị Chủ Trọ Minh Bạch</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight">
              Quản lý Nhà trọ & Tính cước minh bạch
            </h1>
            <p className="text-slate-300 text-sm mt-1.5 max-w-2xl leading-relaxed">
              Tự động áp dụng giá bán lẻ điện sinh hoạt bậc thang theo Quyết định 1279/QĐ-BCT và Nghị định 104/2022/NĐ-CP, bảo vệ cả chủ trọ và khách thuê.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setShowAddPropModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-primary-600/30 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Thêm khu trọ mới</span>
            </button>
          </div>
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

      {/* Property Selector Tabs */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Home className="w-5 h-5 text-primary-600" />
            <span>Danh sách Khu trọ ({propertiesList.length})</span>
          </h2>
          <button
            onClick={fetchProperties}
            title="Làm mới"
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {loadingProps ? (
          <div className="p-8 text-center text-slate-400 text-sm">Đang tải danh sách khu trọ...</div>
        ) : propertiesList.length === 0 ? (
          <div className="p-8 border-2 border-dashed border-slate-200 rounded-2xl text-center bg-white">
            <Building2 className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-700">Chưa có khu trọ nào</p>
            <p className="text-xs text-slate-400 mt-1 mb-4">Bấm nút bên dưới để tạo khu trọ đầu tiên của bạn</p>
            <button
              onClick={() => setShowAddPropModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white text-xs font-bold rounded-xl"
            >
              <Plus className="w-4 h-4" />
              <span>Tạo khu trọ ngay</span>
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3 overflow-x-auto pb-2 scrollbar-thin">
            {propertiesList.map((p) => {
              const active = selectedProperty?.id === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedProperty(p)}
                  className={`px-4 py-3 rounded-2xl border text-left whitespace-nowrap transition-all flex items-center gap-3 ${
                    active
                      ? 'border-primary-600 bg-primary-50/70 text-primary-950 ring-2 ring-primary-500/20 shadow-sm'
                      : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs ${
                      active ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    #{p.id}
                  </div>
                  <div>
                    <p className="text-sm font-bold">{p.name}</p>
                    <p className="text-xs text-slate-500 truncate max-w-[180px]">{p.address || 'Không có địa chỉ'}</p>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Selected Property Details & Rooms */}
      {selectedProperty && (
        <div className="bg-white rounded-3xl shadow-sm border border-slate-200/80 p-6 sm:p-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-black text-slate-900">{selectedProperty.name}</h3>
                <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-700">
                  {roomsList.length} phòng
                </span>
              </div>
              <p className="text-sm text-slate-500 mt-1">
                {selectedProperty.address || 'Chưa cập nhật địa chỉ khu trọ'}
              </p>
            </div>

            <button
              onClick={() => setShowAddRoomModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl transition-all shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Thêm phòng trọ</span>
            </button>
          </div>

          {/* Rooms Grid */}
          {loadingRooms ? (
            <div className="p-8 text-center text-slate-400 text-sm">Đang tải danh sách phòng...</div>
          ) : roomsList.length === 0 ? (
            <div className="p-10 border-2 border-dashed border-slate-200 rounded-2xl text-center">
              <Home className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-700">Khu trọ này chưa có phòng nào</p>
              <p className="text-xs text-slate-400 mt-1 mb-4">Hãy thêm phòng để quản lý chỉ số điện nước</p>
              <button
                onClick={() => setShowAddRoomModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white text-xs font-bold rounded-xl"
              >
                <Plus className="w-4 h-4" />
                <span>Thêm phòng đầu tiên</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {roomsList.map((room) => {
                const isOccupied = room.status === 'active' || room.tenant_id != null;
                return (
                  <div
                    key={room.id}
                    className="p-5 rounded-2xl border border-slate-200/90 bg-slate-50/50 hover:bg-white hover:border-slate-300 hover:shadow-md transition-all flex flex-col justify-between space-y-4"
                  >
                    <div>
                      {/* Room Header */}
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-lg font-black text-slate-900">Phòng {room.room_number}</span>
                        <span
                          className={`px-2.5 py-0.5 text-xs font-bold rounded-full ${
                            isOccupied
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : 'bg-slate-200 text-slate-700'
                          }`}
                        >
                          {isOccupied ? 'Đang thuê' : 'Trống'}
                        </span>
                      </div>

                      {/* Room Details */}
                      <div className="space-y-2 text-xs text-slate-600">
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1.5 text-slate-500">
                            <Users className="w-3.5 h-3.5" />
                            <span>Số người đăng ký định mức:</span>
                          </span>
                          <span className="font-bold text-slate-800">{room.current_people_count} người</span>
                        </div>

                        <div className="flex items-center justify-between">
                          <span className="text-slate-500">Mã mời phòng:</span>
                          <button
                            onClick={() => handleCopy(room.invite_code, `invite-${room.id}`)}
                            title="Sao chép mã mời"
                            className="inline-flex items-center gap-1 font-mono font-bold text-primary-700 hover:text-primary-800 bg-primary-100/70 hover:bg-primary-100 px-2 py-0.5 rounded transition-all"
                          >
                            <span>{room.invite_code}</span>
                            {copiedToken === `invite-${room.id}` ? (
                              <Check className="w-3 h-3 text-emerald-600" />
                            ) : (
                              <Copy className="w-3 h-3 text-slate-400" />
                            )}
                          </button>
                        </div>

                        {isOccupied && (
                          <div className="flex items-center justify-between text-slate-500">
                            <span>Mã khách thuê:</span>
                            <span className="font-mono text-slate-700">#{room.tenant_id}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="pt-3 border-t border-slate-200/80 flex items-center justify-between gap-2">
                      <button
                        onClick={() => {
                          setCalcModalRoom(room);
                          setCalcResult(null);
                        }}
                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white font-semibold text-xs rounded-xl shadow-sm transition-all"
                      >
                        <Calculator className="w-3.5 h-3.5" />
                        <span>Tính hóa đơn</span>
                      </button>

                      {isOccupied && (
                        <button
                          onClick={() => handleRemoveTenant(room.id, room.room_number)}
                          title="Trả phòng & Đổi mã mời"
                          className="px-2.5 py-2 text-slate-400 hover:text-red-600 hover:bg-red-50 border border-slate-200 rounded-xl transition-colors"
                        >
                          <UserX className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* MODAL: Thêm Khu trọ */}
      {showAddPropModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border border-slate-200">
            <h3 className="text-xl font-bold text-slate-900 mb-4">Thêm Khu trọ mới</h3>
            <form onSubmit={handleCreateProperty} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase">
                  Tên Khu trọ / Tòa nhà *
                </label>
                <input
                  type="text"
                  required
                  value={propForm.name}
                  onChange={(e) => setPropForm({ ...propForm, name: e.target.value })}
                  placeholder="Ví dụ: Nhà trọ Minh Khai"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase">
                  Địa chỉ
                </label>
                <input
                  type="text"
                  value={propForm.address}
                  onChange={(e) => setPropForm({ ...propForm, address: e.target.value })}
                  placeholder="Số 123 đường ABC, Quận XYZ, TP. Hà Nội"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddPropModal(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-primary-600 hover:bg-primary-700 text-white font-semibold text-sm rounded-xl"
                >
                  Tạo khu trọ
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Thêm Phòng */}
      {showAddRoomModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border border-slate-200">
            <h3 className="text-xl font-bold text-slate-900 mb-1">
              Thêm phòng cho {selectedProperty?.name}
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Mã mời phòng sẽ tự động được sinh ngẫu nhiên để cung cấp cho người thuê.
            </p>
            <form onSubmit={handleCreateRoom} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase">
                  Số phòng / Tên phòng *
                </label>
                <input
                  type="text"
                  required
                  value={roomForm.room_number}
                  onChange={(e) => setRoomForm({ ...roomForm, room_number: e.target.value })}
                  placeholder="Ví dụ: 101, P202, ..."
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase">
                  Số người đăng ký định mức điện
                </label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  required
                  value={roomForm.current_people_count}
                  onChange={(e) => setRoomForm({ ...roomForm, current_people_count: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Cứ 4 người tạm trú = 1 định mức hộ gia đình theo Thông tư 60/2025/TT-BCT.
                </p>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddRoomModal(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-primary-600 hover:bg-primary-700 text-white font-semibold text-sm rounded-xl"
                >
                  Tạo phòng
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Tính Hóa Đơn & Kiểm Tra Chênh Lệch Thu Lố */}
      {calcModalRoom && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-2xl w-full shadow-2xl border border-slate-200 my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-6">
              <div>
                <div className="text-xs font-bold text-primary-600 uppercase tracking-wider">
                  Tính cước & Sinh hóa đơn minh bạch
                </div>
                <h3 className="text-2xl font-black text-slate-900">
                  Phòng {calcModalRoom.room_number} — {selectedProperty?.name}
                </h3>
              </div>
              <button
                onClick={() => {
                  setCalcModalRoom(null);
                  setCalcResult(null);
                }}
                className="text-slate-400 hover:text-slate-700 font-bold text-lg p-1.5"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCalculateInvoice} className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase">
                    Tháng thanh toán (YYYY-MM) *
                  </label>
                  <input
                    type="month"
                    required
                    value={calcForm.month_year}
                    onChange={(e) => setCalcForm({ ...calcForm, month_year: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase">
                    Phương pháp tính điện
                  </label>
                  <select
                    value={calcForm.elec_method}
                    onChange={(e) => setCalcForm({ ...calcForm, elec_method: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="TIERED">Bậc thang 6 bậc (Luật định - Khuyên dùng)</option>
                    <option value="TIER3">Đồng giá bậc 3 (2.380 đ/kWh)</option>
                  </select>
                </div>
              </div>

              {/* Chỉ số điện */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-700 flex items-center gap-1.5">
                  ⚡ Chỉ số Điện (kWh)
                </span>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-slate-500 mb-1">Chỉ số đầu</label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={calcForm.elec_start}
                      onChange={(e) => setCalcForm({ ...calcForm, elec_start: e.target.value })}
                      placeholder="0"
                      className="w-full px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-500 mb-1">Chỉ số cuối</label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={calcForm.elec_end}
                      onChange={(e) => setCalcForm({ ...calcForm, elec_end: e.target.value })}
                      placeholder="150"
                      className="w-full px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Chỉ số nước */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3">
                <span className="text-xs font-bold uppercase tracking-wider text-blue-700 flex items-center gap-1.5">
                  💧 Chỉ số Nước (m³)
                </span>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-slate-500 mb-1">Chỉ số đầu</label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={calcForm.water_start}
                      onChange={(e) => setCalcForm({ ...calcForm, water_start: e.target.value })}
                      placeholder="0"
                      className="w-full px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-500 mb-1">Chỉ số cuối</label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={calcForm.water_end}
                      onChange={(e) => setCalcForm({ ...calcForm, water_end: e.target.value })}
                      placeholder="5"
                      className="w-full px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Tiền thực thu để đối chiếu thu lố */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase">
                  Số tiền chủ trọ đã thu / dự định thu (VNĐ)
                </label>
                <input
                  type="number"
                  value={calcForm.actual_collected_amount}
                  onChange={(e) => setCalcForm({ ...calcForm, actual_collected_amount: e.target.value })}
                  placeholder="Nhập số tiền thực thu để hệ thống tự động kiểm tra thu lố"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Hệ thống sẽ đối chiếu với giá luật định để phát hiện chênh lệch thu lố.
                </p>
              </div>

              <button
                type="submit"
                disabled={calculating}
                className="w-full py-3 bg-primary-600 hover:bg-primary-700 text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
              >
                {calculating ? (
                  <span className="inline-block animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                ) : (
                  <>
                    <Calculator className="w-4 h-4" />
                    <span>Tính cước ngay & Lưu hóa đơn</span>
                  </>
                )}
              </button>
            </form>

            {/* BREAKDOWN RESULTS & DISPUTE ALERT */}
            {calcResult && (
              <div className="mt-6 pt-6 border-t border-slate-200 space-y-4">
                <h4 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-primary-600" />
                  <span>Kết quả tính toán chi tiết</span>
                </h4>

                {/* Overcharge Alert */}
                {calcResult.diff_amount > 0 ? (
                  <div className="p-4 bg-overcharge-50 border-2 border-overcharge-500/80 rounded-2xl text-overcharge-900 space-y-1.5 shadow-sm">
                    <div className="flex items-center gap-2 font-black text-overcharge-600 text-sm">
                      <ShieldAlert className="w-5 h-5" />
                      <span>CẢNH BÁO: CHÊNH LỆCH THU LỐ {Number(calcResult.diff_amount).toLocaleString('vi-VN')} VNĐ!</span>
                    </div>
                    <p className="text-xs text-overcharge-700 leading-relaxed">
                      Tiền thực thu ({Number(calcResult.actual_collected_amount).toLocaleString('vi-VN')} đ) cao hơn quy định pháp luật ({Number(calcResult.total_statutory_amount).toLocaleString('vi-VN')} đ). Vi phạm quy định tại Nghị định 104/2022/NĐ-CP và có nguy cơ bị xử phạt hành chính từ 20-30 triệu đồng.
                    </p>
                  </div>
                ) : (
                  <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-2xl text-emerald-900 flex items-center gap-2 text-xs font-semibold">
                    <ShieldCheck className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                    <span>Hóa đơn hợp lệ & hoàn toàn minh bạch theo quy định nhà nước.</span>
                  </div>
                )}

                {/* Summary amounts */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <p className="text-[11px] text-slate-500 font-semibold">Tiền điện (VAT 8%)</p>
                    <p className="text-base font-black text-slate-900 mt-1">
                      {Number(calcResult.elec_amount).toLocaleString('vi-VN')} đ
                    </p>
                    <p className="text-[10px] text-slate-400">{calcResult.elec_kwh} kWh</p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <p className="text-[11px] text-slate-500 font-semibold">Tiền nước</p>
                    <p className="text-base font-black text-slate-900 mt-1">
                      {Number(calcResult.water_amount).toLocaleString('vi-VN')} đ
                    </p>
                    <p className="text-[10px] text-slate-400">{calcResult.water_usage} m³</p>
                  </div>

                  <div className="p-3 bg-primary-50 rounded-xl border border-primary-200 col-span-2 sm:col-span-1">
                    <p className="text-[11px] text-primary-700 font-bold">Tổng luật định</p>
                    <p className="text-base font-black text-primary-800 mt-1">
                      {Number(calcResult.total_statutory_amount).toLocaleString('vi-VN')} đ
                    </p>
                  </div>
                </div>

                {/* Public Share Link */}
                {calcResult.share_token && (
                  <div className="p-4 bg-slate-900 text-white rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold text-emerald-400">Link tra cứu công khai (Tính năng 17)</p>
                      <p className="text-[11px] text-slate-300">Khách thuê có thể xem hóa đơn minh bạch không cần đăng nhập</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleCopy(`${window.location.origin}/public/${encodeURIComponent(calcResult.share_token)}`, 'share-link')}
                        className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-colors"
                      >
                        {copiedToken === 'share-link' ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Đã sao chép!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5 text-slate-300" />
                            <span>Sao chép link</span>
                          </>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => onViewPublicInvoice?.(calcResult.share_token)}
                        className="px-3 py-1.5 bg-primary-600 hover:bg-primary-500 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        <span>Xem trang</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
