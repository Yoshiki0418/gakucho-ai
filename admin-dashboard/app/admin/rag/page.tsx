"use client";
import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw, Database } from "lucide-react";
import CSVUploadCard from "./components/CSVUploadCard";
import StatsCards from "./components/StatsCards";
import SourceChart from "./components/SourceChart";
import RecentUpdates from "./components/RecentUpdates";
import { base44 } from "@/lib/base44Client";

export default function RAGDashboard() {
  const [uploadResult, setUploadResult] = useState(null);
  const [stats, setStats] = useState(null);
  const [recentUpdates, setRecentUpdates] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // ✅ FastAPIから統計情報を取得
  const fetchStats = async () => {
    setIsLoading(true);
    try {
      const [statsData, recentData] = await Promise.all([
        base44.rag.getStats(),
        base44.rag.getRecent(),
      ]);
      setStats(statsData);
      setRecentUpdates(recentData);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats(); // 初回ロード時
  }, []);

  // ✅ アップロード完了時に再取得
  const handleUploadComplete = async (result) => {
    setUploadResult(result);
    await fetchStats();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* ヘッダー */}
      <div className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-lg">
              <Database className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">RAG管理ダッシュボード</h1>
              <p className="text-sm text-slate-500 mt-1">知識データベースの管理・更新</p>
            </div>
          </div>
          <Button onClick={fetchStats} variant="outline" className="flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            再読み込み
          </Button>
        </div>
      </div>

      {/* メイン */}
      <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
        <CSVUploadCard onUploadComplete={handleUploadComplete} uploadResult={uploadResult} />

        {/* FastAPIの統計を反映 */}
        <StatsCards
          stats={{
            totalRecords: stats?.total_records ?? 0,
            sourceCount: stats?.source_count ?? 0,
            sourceStats: stats?.source_stats ?? [],
            lastUpdated: stats?.last_updated ? new Date(stats.last_updated) : null,
          }}
          isLoading={isLoading}
        />

          <div className="grid lg:grid-cols-2 gap-6">
            <SourceChart
              data={(stats?.source_stats || []).map((s) => ({
                name: s.source,
                count: Number(s.count),
              }))}
              isLoading={isLoading}
            />
            <RecentUpdates data={recentUpdates} isLoading={isLoading} />
          </div>
      </div>
    </div>
  );
}
