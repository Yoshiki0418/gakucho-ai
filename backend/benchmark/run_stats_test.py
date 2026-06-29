import sys
import pandas as pd
from scipy.stats import mannwhitneyu

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_stats_test.py <csv_path>")
        return
    csv_path = sys.argv[1]
    df = pd.read_csv(csv_path)
    
    # 型変換
    df['ttfa_ms'] = pd.to_numeric(df['ttfa_ms'], errors='coerce')
    
    # 比較する2群のデータ（NaNは除外）
    dynamic = df[df['condition'] == 'dynamic_filler']['ttfa_ms'].dropna()
    off = df[df['condition'] == 'filler_off']['ttfa_ms'].dropna()
    
    # Mann-Whitney U検定 (両側検定)
    # 動的フィラーの方がレイテンシが小さい（早い）ことを示したいが、まずは両側で
    stat, p_value = mannwhitneyu(dynamic, off, alternative='two-sided')
    
    print("=== 統計的有意差検定 (Mann-Whitney U検定) ===")
    print(f"指標: TTFA (Time To First Audio)")
    print(f"群1: dynamic_filler (n={len(dynamic)}), 平均={dynamic.mean():.1f}ms, 中央値={dynamic.median():.1f}ms")
    print(f"群2: filler_off     (n={len(off)}), 平均={off.mean():.1f}ms, 中央値={off.median():.1f}ms")
    print(f"U統計量: {stat}")
    print(f"P値: {p_value:.3e}")
    if p_value < 0.05:
        print("結論: p < 0.05 であり、2群間のTTFAには統計的に有意な差があります。")
    else:
        print("結論: 有意差は認められませんでした。")

if __name__ == "__main__":
    main()
