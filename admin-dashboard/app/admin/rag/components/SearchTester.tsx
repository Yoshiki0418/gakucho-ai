"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { base44 } from "@/lib/base44Client";
import { Search, Loader2, FileText } from "lucide-react";

export default function SearchTester() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setResults([]);

    try {
      const res = await base44.rag.query({ query, top_k: topK });
      setResults(res);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <Card className="border-slate-200 shadow-sm bg-white">
      <CardHeader className="border-b border-slate-100">
        <CardTitle className="flex items-center gap-2 text-xl text-slate-900">
          <Search className="w-5 h-5 text-blue-600" />
          検索テスト
        </CardTitle>
      </CardHeader>

      <CardContent className="pt-6 space-y-6">
        {/* === 検索フォーム === */}
        <div className="flex flex-col lg:flex-row gap-4">
          <Input
            placeholder="例: 奨学金の募集時期は？"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="border-slate-300 flex-1"
          />

          {/* 件数指定 */}
          <div className="flex items-center gap-2 w-full lg:w-32">
            <Input
              type="number"
              min={1}
              max={50}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="border-slate-300"
            />
            <span className="text-sm text-slate-600">件</span>
          </div>

          <Button
            onClick={handleSearch}
            disabled={isSearching}
            className="bg-blue-600 hover:bg-blue-700 text-white w-full lg:w-auto"
          >
            {isSearching ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                検索中...
              </>
            ) : (
              <>
                <Search className="w-4 h-4 mr-2" />
                検索
              </>
            )}
          </Button>
        </div>

        {/* === 検索結果 === */}
        <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
          {results.length > 0 ? (
            results.map((res, idx) => (
              <div
                key={idx}
                className="border border-slate-200 rounded-lg p-4 bg-slate-50 shadow-sm"
              >
                <div className="flex items-start gap-2">
                  <FileText className="w-5 h-5 text-blue-600 mt-1" />
                  <div>
                    <div className="text-slate-700 whitespace-pre-wrap">
                      {res.context}
                    </div>

                    <div className="flex gap-6 text-sm text-slate-500 mt-2">
                      <span>ソース: {res.source}</span>
                      <span>類似度: {res.similarity.toFixed(3)}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            !isSearching && (
              <p className="text-slate-500 text-sm">
                検索結果がここに表示されます
              </p>
            )
          )}
        </div>
      </CardContent>
    </Card>
  );
}
