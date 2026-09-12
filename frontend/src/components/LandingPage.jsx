/*
 * Copyright (c) 2026 tro. Contributors
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useMemo } from 'react';
import {
  Zap,
  Droplets,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  FileSearch,
  CheckCircle2,
  AlertTriangle,
  Building2,
  Users,
  Clock,
  Sparkles,
  Calculator,
} from 'lucide-react';

export default function LandingPage({ onOpenAuth, onOpenPublic }) {
  // Simulator state for live interactive animation
  const [elecStart, setElecStart] = useState(150);
  const [elecEnd, setElecEnd] = useState(295);
  const [peopleCount, setPeopleCount] = useState(2);
  const [actualElecRate, setActualElecRate] = useState(3800); // Landlord rate in VND/kWh

  // Calculate live numbers
  const consumptionKwh = Math.max(0, elecEnd - elecStart);

  // Statutory 6-tier calculation with quota (each 4 people = 1 quota; default 1 person = 1/4 quota)
  const statutoryResult = useMemo(() => {
    const quota = Math.max(1, Math.ceil(peopleCount / 4));
    const baseTiers = [
      { num: 1, limit: 50, price: 1984 },
      { num: 2, limit: 50, price: 2050 },
      { num: 3, limit: 100, price: 2380 },
      { num: 4, limit: 100, price: 2998 },
      { num: 5, limit: 100, price: 3350 },
      { num: 6, limit: Infinity, price: 3460 },
    ];

    let remaining = consumptionKwh;
    let preTax = 0;
    const tierBreakdowns = [];

    for (const t of baseTiers) {
      if (remaining <= 0) break;
      const tierCapacity = t.limit === Infinity ? Infinity : t.limit * quota;
      const usedInTier = Math.min(remaining, tierCapacity);
      const amount = usedInTier * t.price;
      tierBreakdowns.push({
        num: t.num,
        kwh: usedInTier,
        price: t.price,
        amount,
      });
      preTax += amount;
      remaining -= usedInTier;
    }

    const vat = preTax * 0.08; // Nghị quyết 204/2025/QH15
    const totalStatutory = Math.round(preTax + vat);
    const actualCollected = Math.round(consumptionKwh * actualElecRate);
    const diff = actualCollected - totalStatutory;
    const isOvercharged = diff > 0;

    return {
      quota,
      preTax,
      vat,
      totalStatutory,
      actualCollected,
      diff,
      isOvercharged,
      tierBreakdowns,
    };
  }, [consumptionKwh, peopleCount, actualElecRate]);

  return (
    <div className="space-y-16 sm:space-y-24 py-4 sm:py-8">
      {/* Hero Section */}
      <section className="text-center max-w-4xl mx-auto space-y-6">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-50 text-primary-700 text-xs sm:text-sm font-bold border border-primary-200/80 shadow-sm">
          <ShieldCheck className="w-4 h-4 text-primary-600" />
          <span>Hệ thống Quản lý Lưu trú & Đối chiếu Chi phí Điện Nước Minh bạch</span>
        </div>

        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black text-slate-900 tracking-tight leading-[1.15]">
          Chuẩn hóa tiền điện nước, <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-teal-600">
            đối chiếu minh bạch đúng luật định
          </span>
        </h1>

        <p className="text-base sm:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
          Nền tảng đồng hành cùng chủ trọ và người thuê: tự động hóa tính tiền điện bậc thang theo QĐ 1279 & TT 60, đối chiếu tuân thủ Nghị định 104/2022/NĐ-CP, phát hành hóa đơn rõ ràng và chia sẻ tức thì.
        </p>

        {/* Hero CTA buttons */}
        <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4 pt-2">
          <button
            onClick={onOpenAuth}
            className="flex items-center gap-2 px-6 py-3.5 bg-primary-600 hover:bg-primary-700 text-white text-sm sm:text-base font-bold rounded-2xl shadow-lg shadow-primary-500/25 transition-all transform hover:-translate-y-0.5"
          >
            <span>Trải nghiệm ngay</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={onOpenPublic}
            className="flex items-center gap-2 px-5 py-3.5 bg-white hover:bg-slate-50 text-slate-700 text-sm sm:text-base font-bold rounded-2xl border border-slate-200 shadow-sm transition-all"
          >
            <FileSearch className="w-4 h-4 text-slate-500" />
            <span>Tra cứu công khai</span>
          </button>
        </div>
      </section>

      {/* Interactive Visual Simulation Section */}
      <section className="max-w-5xl mx-auto bg-white rounded-3xl border border-slate-200/90 shadow-xl overflow-hidden">
        <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-teal-950 p-6 sm:p-8 text-white">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-teal-400">
                <Sparkles className="w-4 h-4" />
                <span>Mô phỏng Trực quan & Đối chiếu Tức thì</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-black">
                Kiểm tra công tơ & Phát hiện chênh lệch định mức
              </h2>
            </div>
            <span className="text-xs text-slate-300 max-w-xs">
              Thử thay đổi chỉ số công tơ và đơn giá để xem cơ chế đối chiếu tự động hoạt động
            </span>
          </div>
        </div>

        <div className="p-6 sm:p-8 space-y-8">
          {/* Controls grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-1.5">
              <label className="text-xs font-bold text-slate-600 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-500" />
                <span>Chỉ số đầu kỳ (kWh)</span>
              </label>
              <input
                type="number"
                min="0"
                value={elecStart}
                onChange={(e) => setElecStart(Number(e.target.value) || 0)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-base font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-1.5">
              <label className="text-xs font-bold text-slate-600 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-600" />
                <span>Chỉ số cuối kỳ (kWh)</span>
              </label>
              <input
                type="number"
                min={elecStart}
                value={elecEnd}
                onChange={(e) => setElecEnd(Number(e.target.value) || 0)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-base font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-1.5">
              <label className="text-xs font-bold text-slate-600 flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-blue-600" />
                <span>Số người đăng ký</span>
              </label>
              <input
                type="number"
                min="1"
                max="20"
                value={peopleCount}
                onChange={(e) => setPeopleCount(Math.max(1, Number(e.target.value) || 1))}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-base font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-1.5">
              <label className="text-xs font-bold text-slate-600 flex items-center gap-1.5">
                <Calculator className="w-3.5 h-3.5 text-primary-600" />
                <span>Đơn giá chủ thu (đ/kWh)</span>
              </label>
              <input
                type="number"
                step="100"
                value={actualElecRate}
                onChange={(e) => setActualElecRate(Number(e.target.value) || 0)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-base font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* Interactive Visual Flow */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
            {/* Step 1: Consumption Gauge Animation */}
            <div className="p-6 bg-slate-50 rounded-2xl border border-slate-200 flex flex-col justify-between space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase">Bước 1: Tiêu thụ</span>
                <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-100 text-amber-800 rounded-full">
                  Công tơ xoay
                </span>
              </div>

              {/* Animated Meter Dial SVG */}
              <div className="py-2 flex flex-col items-center justify-center">
                <div className="relative w-36 h-36 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      stroke="#e2e8f0"
                      strokeWidth="10"
                      fill="transparent"
                    />
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      stroke="#f59e0b"
                      strokeWidth="10"
                      strokeDasharray="251.2"
                      strokeDashoffset={Math.max(0, 251.2 - (Math.min(consumptionKwh, 300) / 300) * 251.2)}
                      strokeLinecap="round"
                      fill="transparent"
                      className="transition-all duration-700 ease-out"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                    <span className="text-3xl font-black text-slate-900 tracking-tight">
                      {consumptionKwh}
                    </span>
                    <span className="text-[11px] font-bold text-slate-500 uppercase">kWh</span>
                  </div>
                </div>
              </div>

              <div className="text-center text-xs text-slate-600 bg-white p-2.5 rounded-xl border border-slate-200">
                {elecEnd} - {elecStart} = <strong>{consumptionKwh} kWh</strong> điện
              </div>
            </div>

            {/* Step 2: Statutory Progressive Tiers */}
            <div className="p-6 bg-slate-50 rounded-2xl border border-slate-200 flex flex-col justify-between space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase">Bước 2: Áp định mức</span>
                <span className="px-2 py-0.5 text-[10px] font-bold bg-teal-100 text-teal-800 rounded-full">
                  QĐ 1279 / TT 60
                </span>
              </div>

              <div className="space-y-2 text-xs">
                {statutoryResult.tierBreakdowns.map((t) => (
                  <div key={t.num} className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-600">
                      Bậc {t.num} ({t.price.toLocaleString('vi-VN')} đ):
                    </span>
                    <span className="font-bold text-slate-900">
                      {t.kwh} kWh = {t.amount.toLocaleString('vi-VN')} đ
                    </span>
                  </div>
                ))}
                <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-xs">
                  <span className="text-slate-600">Thuế GTGT (8%):</span>
                  <span className="font-semibold text-slate-800">
                    {Math.round(statutoryResult.vat).toLocaleString('vi-VN')} đ
                  </span>
                </div>
              </div>

              <div className="bg-white p-3 rounded-xl border border-slate-200 flex items-center justify-between">
                <span className="text-xs text-slate-500 font-medium">Tổng theo luật:</span>
                <span className="text-base font-black text-primary-700">
                  {statutoryResult.totalStatutory.toLocaleString('vi-VN')} đ
                </span>
              </div>
            </div>

            {/* Step 3: Legal Compliance & Dispute Result */}
            <div
              className={`p-6 rounded-2xl border-2 flex flex-col justify-between space-y-4 transition-all ${
                statutoryResult.isOvercharged
                  ? 'bg-red-50/80 border-red-300 text-red-950'
                  : 'bg-emerald-50/80 border-emerald-300 text-emerald-950'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider">
                  Bước 3: Đối chiếu
                </span>
                <span
                  className={`px-2.5 py-0.5 text-[10px] font-black rounded-full uppercase ${
                    statutoryResult.isOvercharged
                      ? 'bg-red-200 text-red-900'
                      : 'bg-emerald-200 text-emerald-900'
                  }`}
                >
                  {statutoryResult.isOvercharged ? 'Thu lố' : 'Đúng luật'}
                </span>
              </div>

              <div className="space-y-2 text-center py-2">
                {statutoryResult.isOvercharged ? (
                  <div className="space-y-1">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-red-100 text-red-600 mb-1 animate-bounce">
                      <ShieldAlert className="w-6 h-6" />
                    </div>
                    <p className="text-xs font-bold text-red-700 uppercase">Phát hiện thu vượt khung</p>
                    <p className="text-2xl font-black text-red-600">
                      +{statutoryResult.diff.toLocaleString('vi-VN')} đ
                    </p>
                    <p className="text-[11px] text-red-700/90 leading-tight">
                      Nguy cơ vi phạm Nghị định 104/2022/NĐ-CP về thu tiền điện cao hơn quy định
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 mb-1">
                      <ShieldCheck className="w-6 h-6" />
                    </div>
                    <p className="text-xs font-bold text-emerald-700 uppercase">Thu đúng quy định</p>
                    <p className="text-2xl font-black text-emerald-600">0 đ chênh lệch</p>
                    <p className="text-[11px] text-emerald-700/90 leading-tight">
                      Khoản thu hoàn toàn tuân thủ khung giá pháp lý của Bộ Công Thương
                    </p>
                  </div>
                )}
              </div>

              <div className="bg-white/80 backdrop-blur p-2.5 rounded-xl border text-xs flex justify-between">
                <span className="text-slate-600">Chủ trọ thu thực tế:</span>
                <span className="font-black text-slate-900">
                  {statutoryResult.actualCollected.toLocaleString('vi-VN')} đ
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Values Section */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-primary-100 text-primary-700 flex items-center justify-center">
            <Building2 className="w-6 h-6" />
          </div>
          <h3 className="text-base font-black text-slate-900">Dành cho Chủ Trọ</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Lập bản kê nháp kiểm tra trước khi gửi. Hỗ trợ biểu giá chuẩn hoặc đơn giá thỏa thuận, phát hiện vi phạm định mức ngay trên giao diện trước khi xuất hóa đơn.
          </p>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-teal-100 text-teal-700 flex items-center justify-center">
            <Users className="w-6 h-6" />
          </div>
          <h3 className="text-base font-black text-slate-900">Dành cho Người Thuê</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Xem rõ ràng chi tiết chỉ số công tơ đầu kỳ, cuối kỳ, biểu tính từng bậc lũy tiến và đối chiếu chênh lệch minh bạch không còn tranh cãi.
          </p>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-blue-100 text-blue-700 flex items-center justify-center">
            <FileSearch className="w-6 h-6" />
          </div>
          <h3 className="text-base font-black text-slate-900">Tra Cứu Nhanh Không Đăng Nhập</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Mỗi hóa đơn đi kèm Mã tra cứu ngắn (ví dụ: HD-89B2) và link chia sẻ công khai. In hoặc lưu PDF chuẩn A4 100% FOSS không qua phần mềm bên ngoài.
          </p>
        </div>
      </section>
    </div>
  );
}
