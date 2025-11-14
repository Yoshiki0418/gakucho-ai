"use client";

import React, { useState, useRef } from "react";
import { base44 } from "@/lib/base44Client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { format } from "date-fns";

export default function CSVUploadCard({
  onUploadComplete,
  uploadResult,
}: {
  onUploadComplete: (result: any) => void;
  uploadResult: any;
}) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.name.endsWith(".csv")) {
      setSelectedFile(file);
      setError(null);
    } else {
      setError("CSVファイルを選択してください");
      setSelectedFile(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("ファイルを選択してください");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      // ✅ FastAPI /rag/upload にファイル送信（DB登録まで完了）
      const result = await base44.rag.upload(selectedFile);

      if (result.status === "success") {
        onUploadComplete({
          fileName: selectedFile.name,
          uploadDate: new Date(),
          insertedCount: result.insertedCount ?? 0,
          updatedCount: result.updatedCount ?? 0,
          skippedCount: result.skippedCount ?? 0,
        });

        // 入力をリセット
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      } else {
        throw new Error(result.message || "アップロードに失敗しました");
      }
    } catch (err: any) {
      setError(err.message || "アップロード中にエラーが発生しました");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Card className="border-slate-200 shadow-sm bg-white">
      <CardHeader className="border-b border-slate-100">
        <CardTitle className="flex items-center gap-2 text-xl text-slate-900">
          <Upload className="w-5 h-5 text-blue-600" />
          CSVアップロード
        </CardTitle>
      </CardHeader>

      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* === ファイル選択 === */}
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileSelect}
              className="hidden"
            />
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 border-slate-300 hover:bg-slate-50"
              disabled={isUploading}
            >
              <FileText className="w-4 h-4" />
              ファイルを選択
            </Button>
            {selectedFile && (
              <div className="flex items-center gap-2 text-sm text-slate-600 bg-slate-50 px-4 py-2 rounded-lg">
                <FileText className="w-4 h-4" />
                {selectedFile.name}
              </div>
            )}
          </div>

          {/* === アップロードボタン === */}
          <Button
            onClick={handleUpload}
            disabled={!selectedFile || isUploading}
            className="bg-blue-600 hover:bg-blue-700 text-white w-full sm:w-auto"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                アップロード中...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                CSVをアップロード
              </>
            )}
          </Button>

          {/* === エラー表示 === */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* === アップロード結果 === */}
          {uploadResult && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-green-900 mb-2">
                    アップロード完了
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
                    <div className="bg-white rounded-md p-3 border border-green-200">
                      <div className="text-xs text-slate-600">挿入件数</div>
                      <div className="text-2xl font-bold text-green-700">
                        {uploadResult.insertedCount}
                      </div>
                    </div>
                    <div className="bg-white rounded-md p-3 border border-green-200">
                      <div className="text-xs text-slate-600">更新件数</div>
                      <div className="text-2xl font-bold text-blue-700">
                        {uploadResult.updatedCount}
                      </div>
                    </div>
                    <div className="bg-white rounded-md p-3 border border-green-200">
                      <div className="text-xs text-slate-600">スキップ件数</div>
                      <div className="text-2xl font-bold text-slate-700">
                        {uploadResult.skippedCount}
                      </div>
                    </div>
                  </div>

                  <div className="text-sm text-slate-600">
                    <div>ファイル名: {uploadResult.fileName}</div>
                    <div>
                      アップロード日時:{" "}
                      {format(uploadResult.uploadDate, "yyyy年MM月dd日 HH:mm")}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
