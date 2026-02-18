import React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Database, FolderTree, Clock } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";
import { ja } from "date-fns/locale";

export default function StatsCards({ stats, isLoading }) {
  const cards = [
    {
      title: "総レコード数",
      value: stats.totalRecords?.toLocaleString() || "0",
      icon: Database,
      bgColor: "bg-blue-500",
      gradient: "from-blue-500 to-blue-600"
    },
    {
      title: "ソース種別数",
      value: stats.sourceCount?.toLocaleString() || "0",
      icon: FolderTree,
      bgColor: "bg-indigo-500",
      gradient: "from-indigo-500 to-indigo-600"
    },
    {
      title: "最終更新日時",
      value: stats.lastUpdated 
        ? format(stats.lastUpdated, "MM/dd HH:mm", { locale: ja })
        : "-",
      icon: Clock,
      bgColor: "bg-slate-500",
      gradient: "from-slate-500 to-slate-600"
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {cards.map((card, index) => (
        <Card key={index} className="border-slate-200 shadow-sm bg-white overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex justify-between items-start">
              <CardTitle className="text-sm font-medium text-slate-600">
                {card.title}
              </CardTitle>
              <div className={`p-2 rounded-lg bg-gradient-to-br ${card.gradient} bg-opacity-10`}>
                <card.icon className={`w-5 h-5 ${card.bgColor.replace('bg-', 'text-')}`} />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-3xl font-bold text-slate-900">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}