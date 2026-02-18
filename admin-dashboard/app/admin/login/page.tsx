"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Lock } from "lucide-react";

export default function AdminLoginPage() {
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  const onSubmit = (e: any) => {
    e.preventDefault();

    if (
        user === process.env.NEXT_PUBLIC_ADMIN_USER &&
        pass === process.env.NEXT_PUBLIC_ADMIN_PASS
    ) {
        // localStorage ではなく Cookie をセット
        document.cookie = "admin-auth=ok; path=/; max-age=86400";

        router.push("/admin");
    } else {
        setError("ユーザー名またはパスワードが違います");
    }
    };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-blue-100 to-indigo-100 p-4 relative overflow-hidden">

      {/* 🔵 背景の光の粒（Appleっぽい） */}
      <div className="absolute top-[-10%] left-[-10%] w-[350px] h-[350px] rounded-full bg-blue-300/40 blur-3xl" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[350px] h-[350px] rounded-full bg-indigo-300/40 blur-3xl" />

      <Card className="
        w-full max-w-md 
        bg-white/20 
        backdrop-blur-xl 
        border-white/30 
        shadow-[0_0_40px_rgba(0,0,0,0.15)] 
        rounded-3xl 
        relative 
        overflow-hidden
      ">

        {/* Apple風の白い光の筋 */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/40 to-transparent opacity-30 pointer-events-none" />

        <CardHeader>
          <div className="flex items-center gap-3 justify-center relative z-10">
            <div className="
              w-14 h-14 
              bg-gradient-to-br from-blue-600 to-blue-700 
              text-white 
              rounded-2xl 
              flex items-center justify-center 
              shadow-lg 
              backdrop-blur-xl
            ">
              <Lock size={30} />
            </div>
            <h1 className="text-2xl font-semibold text-slate-900 drop-shadow-sm">
              管理者ログイン
            </h1>
          </div>
        </CardHeader>

        <CardContent className="relative z-10">
          <form onSubmit={onSubmit} className="space-y-5">
            <div>
              <p className="text-sm text-slate-700 mb-1">ユーザー名</p>
              <Input
                value={user}
                onChange={(e) => setUser(e.target.value)}
                placeholder="user_name"
                className="
                  bg-white/40 
                  backdrop-blur-lg 
                  border-white/50 
                  text-slate-800 
                  placeholder-slate-500
                "
              />
            </div>

            <div>
              <p className="text-sm text-slate-700 mb-1">パスワード</p>
              <Input
                value={pass}
                onChange={(e) => setPass(e.target.value)}
                placeholder="password"
                type="password"
                className="
                  bg-white/40 
                  backdrop-blur-lg 
                  border-white/50 
                  text-slate-800 
                  placeholder-slate-500
                "
              />
            </div>

            {error && (
              <p className="text-red-600 text-sm text-center">{error}</p>
            )}

            <Button
              className="
                w-full 
                bg-blue-600 hover:bg-blue-700 
                text-white py-2.5 
                rounded-xl 
                shadow-md 
                transition-all
              "
            >
              ログイン
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
