import React, { useState } from 'react'

// ❌ 型エラー（暗黙の any）
// ❌ 不要なanyの使用
// ❌ 関数名がlowercaseではない
export default function page(props) {

console.log("Lint error test")  // ❌ no-console, ❌ セミコロンなし

    const unused = 123    // ❌ 未使用変数
    if (true) 
    {console.log("Bad formatting")}  // ❌ 波括弧とインデント崩れ

  return <div>
  <h1 >  Lint Test Page </h1>  {/* ❌ 余分なスペース・フォーマット */}
<p>this should trigger multiple lint errors</p>
</div>
}