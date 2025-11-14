"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Database, FileText, Mic, RefreshCw, Settings } from "lucide-react";
import Link from "next/link";

export default function AdminDashboard() {
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState({
    ragRecords: 0,
    ragSources: 0,
    lastUpdated: null,
  });

  // ✅ 全体統計の取得（例: /api/admin/stats）
  const fetchStats = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/admin/stats");
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error("Failed to load stats:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* ===== ヘッダー ===== */}
      <div className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-lg">
              <Settings className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">管理ダッシュボード</h1>
              <p className="text-sm text-slate-500 mt-1">全システムの統合管理</p>
            </div>
          </div>
          <Button onClick={fetchStats} variant="outline" className="flex items-center gap-2">
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            再読み込み
          </Button>
        </div>
      </div>

      {/* ===== メインコンテンツ ===== */}
      <div className="max-w-7xl mx-auto px-4 py-10 space-y-8">
        {/* 統計情報カード */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="p-6 bg-white rounded-2xl shadow-sm border border-slate-200">
            <h3 className="text-sm font-semibold text-slate-600 mb-1">RAG登録データ数</h3>
            <p className="text-3xl font-bold text-blue-600">{stats.ragRecords}</p>
          </div>
          <div className="p-6 bg-white rounded-2xl shadow-sm border border-slate-200">
            <h3 className="text-sm font-semibold text-slate-600 mb-1">RAGソース数</h3>
            <p className="text-3xl font-bold text-indigo-600">{stats.ragSources}</p>
          </div>
          <div className="p-6 bg-white rounded-2xl shadow-sm border border-slate-200">
            <h3 className="text-sm font-semibold text-slate-600 mb-1">最終更新</h3>
            <p className="text-md text-slate-800">
              {stats.lastUpdated
                ? new Date(stats.lastUpdated).toLocaleString("ja-JP")
                : "—"}
            </p>
          </div>
        </div>

        {/* 管理モジュールへのナビゲーション */}
        <div className="grid md:grid-cols-3 gap-6">
          <Link
            href="/admin/rag"
            className="group bg-white border border-slate-200 hover:border-blue-400 transition rounded-2xl p-6 shadow-sm hover:shadow-md flex flex-col items-center text-center"
          >
            <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-4">
              <Database className="w-7 h-7 text-white" />
            </div>
            <h3 className="text-lg font-bold text-slate-800 group-hover:text-blue-600 transition">
              RAGデータ管理
            </h3>
            <p className="text-sm text-slate-500 mt-2">知識ベースの登録・統計管理</p>
          </Link>

          <div className="group bg-white border border-slate-200 hover:border-blue-400 transition rounded-2xl p-6 shadow-sm hover:shadow-md flex flex-col items-center text-center cursor-not-allowed opacity-70">
            <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center mb-4">
              <Mic className="w-7 h-7 text-white" />
            </div>
            <h3 className="text-lg font-bold text-slate-800">音声データ管理</h3>
            <p className="text-sm text-slate-500 mt-2">※近日追加予定</p>
          </div>

          <div className="group bg-white border border-slate-200 hover:border-blue-400 transition rounded-2xl p-6 shadow-sm hover:shadow-md flex flex-col items-center text-center cursor-not-allowed opacity-70">
            <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center mb-4">
              <FileText className="w-7 h-7 text-white" />
            </div>
            <h3 className="text-lg font-bold text-slate-800">ログ・レポート</h3>
            <p className="text-sm text-slate-500 mt-2">※近日追加予定</p>
          </div>
        </div>
      </div>
    </div>
  );
}
