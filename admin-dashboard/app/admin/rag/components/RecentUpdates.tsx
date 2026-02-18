import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Clock, FileText } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";
import { ja } from "date-fns/locale";

export default function RecentUpdates({ data = [], isLoading }) {
  const truncateText = (text, maxLength = 80) => {
    if (!text) return "-";
    return text.length > maxLength ? text.slice(0, maxLength) + "..." : text;
  };

  // ✅ 日時があれば降順にソート
  const sortedData = [...data]
    .filter(Boolean)
    .sort((a, b) => new Date(b.updated_at || b.uploadDate || 0) - new Date(a.updated_at || a.uploadDate || 0))
    .slice(0, 10); // 最新10件

  return (
    <Card className="border-slate-200 shadow-sm bg-white">
      <CardHeader className="border-b border-slate-100">
        <CardTitle className="flex items-center gap-2 text-lg text-slate-900">
          <Clock className="w-5 h-5 text-blue-600" />
          最近の更新履歴（最新10件）
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-6">
        {/* === ローディング時 === */}
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex gap-3">
                <Skeleton className="h-4 flex-1" />
                <Skeleton className="h-4 w-24" />
              </div>
            ))}
          </div>
        ) : sortedData.length === 0 ? (
          /* === データなし === */
          <div className="flex flex-col items-center justify-center py-12 text-slate-400">
            <FileText className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm">更新履歴がありません</p>
          </div>
        ) : (
          /* === データ表示 === */
          <div className="overflow-x-auto max-h-[300px]">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50 border-slate-200">
                  <TableHead className="text-slate-700 font-semibold w-1/2">内容</TableHead>
                  <TableHead className="text-slate-700 font-semibold">ソース</TableHead>
                  <TableHead className="text-slate-700 font-semibold whitespace-nowrap">更新日時</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((item, i) => {
                  const updatedAt = item.updated_at || item.uploadDate;
                  return (
                    <TableRow key={i} className="hover:bg-slate-50 transition-colors">
                      <TableCell className="text-slate-700">
                        <div className="flex items-start gap-2">
                          <FileText className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                          <span className="text-sm">{truncateText(item.context || item.message)}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-slate-600 text-sm">
                        {item.source || "-"}
                      </TableCell>
                      <TableCell className="text-slate-500 text-sm whitespace-nowrap">
                        {updatedAt
                          ? format(new Date(updatedAt), "yyyy/MM/dd HH:mm", { locale: ja })
                          : "-"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
