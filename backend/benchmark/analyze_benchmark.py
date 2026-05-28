"""
ベンチマーク結果の分析・可視化スクリプト。

benchmark_runner.py が出力した CSV を読み込み、
統計サマリとグラフを生成する。

Usage:
    python -m benchmark.analyze_benchmark --input data/benchmark_results/benchmark_YYYYMMDD_HHMMSS.csv
    python -m benchmark.analyze_benchmark --input data/benchmark_results/benchmark_YYYYMMDD_HHMMSS.csv --no-show
"""

import argparse
import os
import sys

import pandas as pd

# matplotlib は日本語フォント設定のため遅延 import
_plt = None
_np = None


def _init_matplotlib():
    global _plt
    if _plt is not None:
        return
    import matplotlib
    matplotlib.use("Agg")  # GUI不要
    import matplotlib.pyplot as plt
    # 日本語フォント設定（利用可能なら）
    try:
        import matplotlib.font_manager as fm
        jp_fonts = [f.name for f in fm.fontManager.ttflist
                    if "Gothic" in f.name or "Meiryo" in f.name or "Noto" in f.name]
        if jp_fonts:
            plt.rcParams["font.family"] = jp_fonts[0]
    except Exception:
        pass
    plt.rcParams["font.size"] = 12
    plt.rcParams["figure.figsize"] = (12, 6)
    plt.rcParams["figure.dpi"] = 150
    _plt = plt


def _init_numpy():
    global _np
    if _np is None:
        import numpy as np
        _np = np


def load_results(csv_path: str) -> pd.DataFrame:
    """CSV を読み込み、型変換を行う。"""
    df = pd.read_csv(csv_path)

    # 数値カラムの型変換
    numeric_cols = [
        "ttft_ms", "ttfa_ms", "ttmr_ms", "total_ms",
        "filler_duration_ms", "classifier_ms",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ブール値の変換
    bool_cols = ["filler_fired", "main_responded_in_time", "filler_enabled"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().map(
                {"true": True, "false": False, "1": True, "0": False}
            )

    return df


def print_summary(df: pd.DataFrame) -> str:
    """統計サマリをコンソールに表示し、テキストとしても返す。"""
    lines = []
    lines.append("=" * 70)
    lines.append("ベンチマーク結果サマリ")
    lines.append("=" * 70)
    lines.append(f"  総データ数: {len(df)}")
    lines.append(f"  条件: {df['condition'].unique().tolist()}")
    lines.append(f"  カテゴリ: {df['category'].unique().tolist()}")
    lines.append("")

    # --- 条件別の全体統計 ---
    lines.append("-" * 70)
    lines.append("■ 条件別レイテンシ統計 (ms)")
    lines.append("-" * 70)

    metrics = ["ttft_ms", "ttfa_ms", "ttmr_ms", "total_ms"]
    for cond in sorted(df["condition"].unique()):
        subset = df[df["condition"] == cond]
        lines.append(f"\n  【{cond}】 (n={len(subset)})")
        for metric in metrics:
            if metric not in subset.columns:
                continue
            vals = subset[metric].dropna()
            if vals.empty:
                continue
            lines.append(
                f"    {metric:20s}: "
                f"mean={vals.mean():7.0f}  "
                f"median={vals.median():7.0f}  "
                f"P95={vals.quantile(0.95):7.0f}  "
                f"P99={vals.quantile(0.99):7.0f}  "
                f"std={vals.std():7.0f}"
            )

        # フィラー発火率
        if "filler_fired" in subset.columns:
            filler_rate = subset["filler_fired"].sum() / len(subset) * 100
            lines.append(f"    {'filler_fired_rate':20s}: {filler_rate:6.1f}%")

    # --- カテゴリ別 × 条件別 ---
    lines.append("")
    lines.append("-" * 70)
    lines.append("■ カテゴリ別 × 条件別 TTFT (ms)")
    lines.append("-" * 70)

    pivot = df.pivot_table(
        values="ttft_ms",
        index="category",
        columns="condition",
        aggfunc=["mean", "median", "std", "count"],
    )
    lines.append(pivot.to_string())

    # --- フィラー発火率（カテゴリ別） ---
    if "filler_fired" in df.columns:
        lines.append("")
        lines.append("-" * 70)
        lines.append("■ カテゴリ別フィラー発火率")
        lines.append("-" * 70)

        for cond in sorted(df["condition"].unique()):
            subset = df[df["condition"] == cond]
            lines.append(f"\n  【{cond}】")
            for cat in sorted(subset["category"].unique()):
                cat_data = subset[subset["category"] == cat]
                fired = cat_data["filler_fired"].sum()
                total = len(cat_data)
                rate = fired / total * 100 if total > 0 else 0
                lines.append(f"    {cat:20s}: {fired}/{total} ({rate:.0f}%)")

    output = "\n".join(lines)
    print(output)
    return output


def plot_ttft_comparison(df: pd.DataFrame, output_dir: str):
    """条件別の TTFT 棒グラフ（カテゴリ別）を生成。"""
    _init_matplotlib()
    _init_numpy()

    fig, ax = _plt.subplots(figsize=(14, 6))

    conditions = sorted(df["condition"].unique())
    categories = sorted(df["category"].unique())

    x = _np.arange(len(categories))
    width = 0.35
    colors = ["#1565C0", "#FF6F00", "#2E7D32"]

    for i, cond in enumerate(conditions):
        subset = df[df["condition"] == cond]
        means = [subset[subset["category"] == cat]["ttft_ms"].mean() for cat in categories]
        stds = [subset[subset["category"] == cat]["ttft_ms"].std() for cat in categories]
        offset = (i - len(conditions) / 2 + 0.5) * width
        bars = ax.bar(x + offset, means, width, yerr=stds, label=cond,
                      color=colors[i % len(colors)], alpha=0.85, capsize=4)
        # 値ラベル
        for bar, mean in zip(bars, means):
            if not _np.isnan(mean):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
                        f"{mean:.0f}", ha="center", va="bottom", fontsize=9)

    ax.set_xlabel("Query Category")
    ax.set_ylabel("TTFT (ms)")
    ax.set_title("Time To First Text (TTFT) - Condition Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=30, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    path = os.path.join(output_dir, "ttft_comparison.png")
    fig.savefig(path)
    _plt.close(fig)
    print(f"  [SAVED] {path}")


def plot_latency_boxplot(df: pd.DataFrame, output_dir: str):
    """条件別のレイテンシ分布（箱ひげ図）を生成。"""
    _init_matplotlib()

    metrics = ["ttft_ms", "ttfa_ms", "total_ms"]
    conditions = sorted(df["condition"].unique())

    fig, axes = _plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 6))
    if len(metrics) == 1:
        axes = [axes]

    colors = ["#1565C0", "#FF6F00", "#2E7D32"]

    for ax, metric in zip(axes, metrics):
        data_by_cond = []
        labels = []
        for cond in conditions:
            vals = df[df["condition"] == cond][metric].dropna()
            data_by_cond.append(vals)
            labels.append(cond)

        bp = ax.boxplot(data_by_cond, labels=labels, patch_artist=True)
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        ax.set_ylabel("Latency (ms)")
        ax.set_title(metric)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Latency Distribution by Condition", fontsize=14, y=1.02)
    fig.tight_layout()

    path = os.path.join(output_dir, "latency_boxplot.png")
    fig.savefig(path, bbox_inches="tight")
    _plt.close(fig)
    print(f"  [SAVED] {path}")


def plot_filler_fire_rate(df: pd.DataFrame, output_dir: str):
    """カテゴリ別のフィラー発火率棒グラフを生成。"""
    _init_matplotlib()
    _init_numpy()

    if "filler_fired" not in df.columns:
        return

    conditions = sorted(df["condition"].unique())
    categories = sorted(df["category"].unique())

    fig, ax = _plt.subplots(figsize=(12, 6))
    x = _np.arange(len(categories))
    width = 0.35
    colors = ["#1565C0", "#FF6F00", "#2E7D32"]

    for i, cond in enumerate(conditions):
        subset = df[df["condition"] == cond]
        rates = []
        for cat in categories:
            cat_data = subset[subset["category"] == cat]
            if len(cat_data) > 0:
                rate = cat_data["filler_fired"].sum() / len(cat_data) * 100
            else:
                rate = 0
            rates.append(rate)

        offset = (i - len(conditions) / 2 + 0.5) * width
        bars = ax.bar(x + offset, rates, width, label=cond,
                      color=colors[i % len(colors)], alpha=0.85)
        for bar, rate in zip(bars, rates):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f"{rate:.0f}%", ha="center", va="bottom", fontsize=9)

    ax.set_xlabel("Query Category")
    ax.set_ylabel("Filler Fire Rate (%)")
    ax.set_title("Filler Activation Rate by Category and Condition")
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=30, ha="right")
    ax.set_ylim(0, 110)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    path = os.path.join(output_dir, "filler_fire_rate.png")
    fig.savefig(path)
    _plt.close(fig)
    print(f"  [SAVED] {path}")


def plot_psd_scatter(df: pd.DataFrame, output_dir: str):
    """
    TTMR（本応答遅延）vs TTFT（体感応答開始）の散布図。
    フィラー発火/非発火で色分けし、フィラーによるPSD短縮効果を可視化。
    """
    _init_matplotlib()

    if "ttmr_ms" not in df.columns or "ttft_ms" not in df.columns:
        return

    fig, ax = _plt.subplots(figsize=(10, 8))

    # フィラーあり条件のみ
    filler_on = df[df["condition"] == "filler_on"].copy()
    if filler_on.empty:
        _plt.close(fig)
        return

    fired = filler_on[filler_on["filler_fired"] == True]
    not_fired = filler_on[filler_on["filler_fired"] == False]

    if not not_fired.empty:
        ax.scatter(
            not_fired["ttmr_ms"], not_fired["ttft_ms"],
            c="#1565C0", alpha=0.7, s=60, label="Filler not fired",
            edgecolors="white", linewidth=0.5,
        )
    if not fired.empty:
        ax.scatter(
            fired["ttmr_ms"], fired["ttft_ms"],
            c="#FF6F00", alpha=0.7, s=60, label="Filler fired",
            edgecolors="white", linewidth=0.5,
        )

    # 対角線（TTFT == TTMR → フィラーなしと同じ）
    lims = [0, max(ax.get_xlim()[1], ax.get_ylim()[1])]
    ax.plot(lims, lims, "--", color="gray", alpha=0.5, label="TTFT = TTMR (no filler effect)")

    ax.set_xlabel("TTMR - Time To Main Response (ms)")
    ax.set_ylabel("TTFT - Time To First Text (ms)")
    ax.set_title("Filler Effect: TTMR vs TTFT\n(Points below diagonal = filler reduced perceived delay)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()

    path = os.path.join(output_dir, "psd_scatter.png")
    fig.savefig(path)
    _plt.close(fig)
    print(f"  [SAVED] {path}")


def generate_all(csv_path: str, output_dir: str | None = None):
    """全分析を実行する。"""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(csv_path), "figures")
    os.makedirs(output_dir, exist_ok=True)

    print(f"入力: {csv_path}")
    print(f"出力: {output_dir}")
    print()

    # データ読み込み
    df = load_results(csv_path)
    print(f"データ件数: {len(df)}")
    print()

    # 統計サマリ
    summary_text = print_summary(df)

    # サマリをテキストファイルにも保存
    summary_path = os.path.join(output_dir, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    print(f"\n  [SAVED] {summary_path}")

    # グラフ生成
    print("\nグラフ生成中...")
    try:
        plot_ttft_comparison(df, output_dir)
    except Exception as e:
        print(f"  [WARN] TTFT comparison plot failed: {e}")

    try:
        plot_latency_boxplot(df, output_dir)
    except Exception as e:
        print(f"  [WARN] Latency boxplot failed: {e}")

    try:
        plot_filler_fire_rate(df, output_dir)
    except Exception as e:
        print(f"  [WARN] Filler fire rate plot failed: {e}")

    try:
        plot_psd_scatter(df, output_dir)
    except Exception as e:
        print(f"  [WARN] PSD scatter plot failed: {e}")

    print("\n=== 分析完了 ===")


def main():
    parser = argparse.ArgumentParser(
        description="Gakucho-AI ベンチマーク結果分析ツール"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="benchmark_runner.py が出力した CSV ファイルのパス",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="グラフ出力先ディレクトリ（デフォルト: CSVと同じディレクトリの figures/）",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERROR] ファイルが見つかりません: {args.input}")
        sys.exit(1)

    generate_all(args.input, args.output_dir)


if __name__ == "__main__":
    main()
