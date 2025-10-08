import 'styled-components';
import theme from './theme';

// theme の型を typeof で抽出
type ThemeType = typeof theme;

// styled-components の DefaultTheme にマージ
declare module 'styled-components' {
  export interface DefaultTheme extends ThemeType {}
}