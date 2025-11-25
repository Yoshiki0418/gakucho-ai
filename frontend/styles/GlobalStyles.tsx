import { createGlobalStyle } from "styled-components";

const GlobalStyles = createGlobalStyle`
* {
    box-sizing: border-box;
    /* font-family: 'Crimson Text', serif;  */
  }

  html, body, div, span, applet, object, iframe,
  h1, h2, h3, h4, h5, h6, p, blockquote, pre,
  a, abbr, acronym, address, big, cite, code,
  del, dfn, em, img, ins, kbd, q, s, samp,
  small, strike, strong, sub, sup, tt, var,
  b, u, i, center,
  dl, dt, dd, ol, ul, li,
  fieldset, form, label, legend,
  table, caption, tbody, tfoot, thead, tr, th, td,
  article, aside, canvas, details, embed,
  figure, figcaption, footer, header, hgroup,
  menu, nav, output, ruby, section, summary,
  time, mark, audio, video,input {
    margin: 0;
    padding: 0;
    border: 0;
    vertical-align: baseline;
    font-family: "OpenAI Sans", "Google Sans", "Helvetica Neue", sans-serif;
    text-decoration:none;
    color:black;
  }

  article, aside, details, figcaption, figure,
  footer, header, hgroup, menu, nav, section {
    display: block;
  }
  body {
    line-height: 1;
  }
  ol, ul {
    list-style: none;
  }
  blockquote, q {
    quotes: none;
  }
  blockquote:before, blockquote:after,
  q:before, q:after {
    content: '';
    content: none;
  }
  table {
    border-collapse: collapse;
    border-spacing: 0;
  }

button {
  appearance: none; /* ブラウザのデフォルトスタイルを削除 */
  -webkit-appearance: none; /* Safari用のリセット */
  -moz-appearance: none; /* Firefox用のリセット */
  border: none; /* デフォルトの枠線を削除 */
  padding: 0; /* デフォルトのパディングを削除 */
  background: none; /* 背景をリセット */
  font-family: 'Crimson Text', serif;
}

.gakucho-markdown {
  color: #E5E7EB; /* デフォルト色（assistant のメッセージ） */
}

.gakucho-markdown * {
  color: inherit !important;
}

.gakucho-markdown code {
  background: rgba(255,255,255,0.1);
  padding: 2px 4px;
  border-radius: 4px;
  font-family: monospace;
}
`

export default GlobalStyles