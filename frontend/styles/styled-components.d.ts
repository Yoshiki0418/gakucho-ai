import 'styled-components';
import theme from './theme';

// theme の型を typeof で抽出
type ThemeType = typeof theme;

// styled-components の DefaultTheme にマージ
declare module 'styled-components' {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  export interface DefaultTheme extends ThemeType {}
}
