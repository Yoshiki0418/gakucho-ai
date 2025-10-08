// 共通のフォントサイズ定義
const fontSize = {
    Small: '1.0625rem',  // 16px
    Medium: '1.25rem', // 20px
    Large: '1.5rem', //24px
    ExtraLarge: '2rem', // 32px
    flexible: {
        Large: 'clamp(1.5rem, calc(1.5rem + .375*((100vw - 23.4375rem) / 66.5625)), 1.875rem)',
        ExtraLarge: 'clamp(2rem, calc(2rem + 2*((100vw - 23.4375rem) / 66.5625)), 3.45rem)',
    }
}

export default fontSize
