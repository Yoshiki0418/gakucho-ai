import { Base44 } from "base44-sdk"; // 仮のSDK名

export const base44 = new Base44({
  apiKey: process.env.NEXT_PUBLIC_BASE44_API_KEY,
});