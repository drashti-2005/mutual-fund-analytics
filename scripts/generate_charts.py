"""
generate_charts.py — Day 3: Export all 18 EDA charts as PNG using matplotlib only.
Run: python scripts/generate_charts.py
No kaleido, no Jupyter, no Plotly write_image — all matplotlib/seaborn.
"""
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[1]
PROC        = ROOT / "data" / "processed"
CHARTS_DIR  = ROOT / "reports" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Style ──────────────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
plt.rcParams.update({"figure.dpi": 150})

def save(fig, name):
    fig.savefig(CHARTS_DIR / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {name}")

print("Loading data...")
fund_master  = pd.read_csv(PROC / "01_fund_master_clean.csv")
nav_history  = pd.read_csv(PROC / "02_nav_history_clean.csv", parse_dates=["date"])
aum_data     = pd.read_csv(PROC / "03_aum_by_fund_house_clean.csv", parse_dates=["date"])
sip_inflows  = pd.read_csv(PROC / "04_monthly_sip_inflows_clean.csv", parse_dates=["month"])
cat_inflows  = pd.read_csv(PROC / "05_category_inflows_clean.csv", parse_dates=["month"])
folio_count  = pd.read_csv(PROC / "06_industry_folio_count_clean.csv", parse_dates=["month"])
performance  = pd.read_csv(PROC / "07_scheme_performance_clean.csv")
transactions = pd.read_csv(PROC / "08_investor_transactions_clean.csv", parse_dates=["transaction_date"])
portfolio    = pd.read_csv(PROC / "09_portfolio_holdings_clean.csv")
benchmark    = pd.read_csv(PROC / "10_benchmark_indices_clean.csv", parse_dates=["date"])
transactions["transaction_type"] = transactions["transaction_type"].str.strip().str.title().replace({"Sip": "SIP"})
print("  Data loaded.\n")

print("Generating charts...")

# ── Chart 1: NAV Trend (sample weekly for speed, all schemes) ──────────────
nav_merged = nav_history.merge(fund_master[["amfi_code","scheme_name"]], on="amfi_code", how="left")
nav_merged["short"] = nav_merged["scheme_name"].str.replace(r" - (Regular|Direct) Plan.*","",regex=True).str.slice(0,25)
nav_sampled = nav_merged.sort_values(["amfi_code","date"]).groupby("amfi_code").apply(lambda x: x.iloc[::7]).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(16, 7))
for name, grp in nav_sampled.groupby("short"):
    ax.plot(grp["date"], grp["nav"], lw=0.8, alpha=0.7)
ax.axvspan(pd.Timestamp("2023-01-01"), pd.Timestamp("2023-12-31"), alpha=0.08, color="green", label="2023 Bull Run")
ax.axvspan(pd.Timestamp("2024-04-01"), pd.Timestamp("2024-09-30"), alpha=0.08, color="red", label="2024 Correction")
ax.set_title("Daily NAV Trend — All Mutual Fund Schemes (2022–2026)", fontsize=14, fontweight="bold")
ax.set_xlabel("Date"); ax.set_ylabel("NAV (₹)")
ax.legend(fontsize=9, loc="upper left"); plt.tight_layout()
save(fig, "01_nav_trend.png")

# ── Chart 2: AUM Growth ────────────────────────────────────────────────────
aum_data["year"] = aum_data["date"].dt.year
aum_yearly = aum_data.groupby(["year","fund_house"])["aum_lakh_crore"].mean().reset_index()
fig, ax = plt.subplots(figsize=(14, 7))
sns.barplot(data=aum_yearly, x="fund_house", y="aum_lakh_crore", hue="year", palette="muted", ax=ax)
ax.set_title("AUM Growth by Fund House (2022–2025)\nSBI Leads at ₹12.5 Lakh Crore", fontsize=13, fontweight="bold")
ax.set_xlabel("Fund House"); ax.set_ylabel("Avg AUM (₹ Lakh Crore)")
ax.tick_params(axis="x", rotation=45); ax.legend(title="Year", bbox_to_anchor=(1.01,1))
plt.tight_layout(); save(fig, "02_aum_growth.png")

# ── Chart 3: SIP Inflow ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 5))
ax.fill_between(sip_inflows["month"], sip_inflows["sip_inflow_crore"], alpha=0.25, color="#2196F3")
ax.plot(sip_inflows["month"], sip_inflows["sip_inflow_crore"], color="#2196F3", lw=2.5, marker="o", ms=4)
peak = sip_inflows.loc[sip_inflows["sip_inflow_crore"].idxmax()]
ax.annotate(f"All-Time High\n₹{peak['sip_inflow_crore']:,} Cr", xy=(peak["month"], peak["sip_inflow_crore"]),
    xytext=(peak["month"], peak["sip_inflow_crore"]*0.88),
    arrowprops=dict(arrowstyle="->", color="red"), color="red", fontsize=10, ha="center")
ax.set_title("Monthly SIP Inflows — Jan 2022 to Dec 2025 (₹ Crore)", fontsize=13, fontweight="bold")
ax.set_xlabel("Month"); ax.set_ylabel("SIP Inflow (₹ Crore)"); plt.tight_layout()
save(fig, "03_sip_trend.png")

# ── Chart 4: Category Heatmap ─────────────────────────────────────────────
cat_inflows["month_label"] = cat_inflows["month"].dt.strftime("%b-%y")
pivot = cat_inflows.pivot_table(index="category", columns="month_label", values="net_inflow_crore", aggfunc="sum")
month_order = cat_inflows.sort_values("month")["month_label"].unique()
pivot = pivot.reindex(columns=[m for m in month_order if m in pivot.columns])
fig, ax = plt.subplots(figsize=(16, 7))
sns.heatmap(pivot, annot=True, fmt=".0f", cmap="RdYlGn", linewidths=0.5, ax=ax, annot_kws={"size":7})
ax.set_title("Category-wise Net Inflow Heatmap (FY 2024-25)", fontsize=13, fontweight="bold")
ax.tick_params(axis="x", rotation=45); plt.tight_layout()
save(fig, "04_category_heatmap.png")

# ── Chart 5: Demographics ─────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(16, 6))
age_counts = transactions["age_group"].value_counts()
axes[0].pie(age_counts.values, labels=age_counts.index, autopct="%1.1f%%", startangle=90)
axes[0].set_title("Age Group Distribution")
gender_counts = transactions["gender"].value_counts()
axes[1].pie(gender_counts.values, labels=gender_counts.index, autopct="%1.1f%%",
    colors=["#42A5F5","#EC407A"], startangle=90)
axes[1].set_title("Gender Distribution")
sip_txns = transactions[transactions["transaction_type"]=="SIP"]
age_order = ["18-25","26-35","36-45","46-55","56+"]
data_box = [sip_txns[sip_txns["age_group"]==a]["amount_inr"].dropna().values for a in age_order]
axes[2].boxplot(data_box, labels=age_order, showfliers=False)
axes[2].set_title("SIP Amount by Age Group"); axes[2].set_ylabel("Amount (₹)")
fig.suptitle("Investor Demographics — Age, Gender & SIP Amounts", fontsize=13, fontweight="bold")
plt.tight_layout(); save(fig, "05_demographics.png")

# ── Chart 6: Geographic ───────────────────────────────────────────────────
state_data = (transactions.groupby("state")["amount_inr"].sum().div(1e7).reset_index()
    .rename(columns={"amount_inr":"total_crore"}).sort_values("total_crore"))
city_tier = transactions.groupby("city_tier")["amount_inr"].sum()
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), gridspec_kw={"width_ratios":[2,1]})
ax1.barh(state_data["state"], state_data["total_crore"], color="#42A5F5")
ax1.set_title("Total Investment by State (₹ Crore)"); ax1.set_xlabel("₹ Crore")
ax2.pie(city_tier.values, labels=city_tier.index, autopct="%1.1f%%",
    colors=["#FF7043","#66BB6A"], startangle=90)
ax2.set_title("T30 vs B30 City Split")
plt.tight_layout(); save(fig, "06_geo_distribution.png")

# ── Chart 7: Folio Growth ─────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 6))
colors = {"equity_folios_crore":"#1976D2","debt_folios_crore":"#F57C00",
          "hybrid_folios_crore":"#388E3C","others_folios_crore":"#7B1FA2"}
labels = {"equity_folios_crore":"Equity","debt_folios_crore":"Debt",
          "hybrid_folios_crore":"Hybrid","others_folios_crore":"Others"}
bottom = np.zeros(len(folio_count))
for col, color in colors.items():
    ax.fill_between(folio_count["month"], bottom, bottom + folio_count[col].values,
        label=labels[col], color=color, alpha=0.8)
    bottom += folio_count[col].values
ax.set_title("Mutual Fund Folio Count Growth — Jan 2022 to Dec 2025", fontsize=13, fontweight="bold")
ax.set_xlabel("Month"); ax.set_ylabel("Folios (Crore)"); ax.legend(); plt.tight_layout()
save(fig, "07_folio_growth.png")

# ── Chart 8: Correlation Matrix ───────────────────────────────────────────
top10 = nav_history.groupby("amfi_code")["date"].count().nlargest(10).index.tolist()
pivot_r = (nav_history[nav_history["amfi_code"].isin(top10)]
    .pivot_table(index="date", columns="amfi_code", values="daily_return_pct")
    .dropna(thresh=8).fillna(method="ffill").dropna())
code_to_name = fund_master.set_index("amfi_code")["scheme_name"].str.replace(r" - (Regular|Direct) Plan.*","",regex=True).str.slice(0,18)
pivot_r.columns = [code_to_name.get(c, str(c)) for c in pivot_r.columns]
corr = pivot_r.corr()
fig, ax = plt.subplots(figsize=(12, 9))
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", mask=mask, ax=ax,
    linewidths=0.5, vmin=-1, vmax=1, cbar_kws={"label":"Pearson Correlation"})
ax.set_title("NAV Daily Return Correlation Matrix — 10 Funds", fontsize=13, fontweight="bold")
plt.tight_layout(); save(fig, "08_correlation_matrix.png")

# ── Chart 9: Sector Allocation ────────────────────────────────────────────
sector_agg = portfolio.groupby("sector")["market_value_cr"].sum().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(10, 8))
wedges, texts, autotexts = ax.pie(sector_agg.values, labels=sector_agg.index,
    autopct="%1.1f%%", startangle=90, pctdistance=0.82,
    wedgeprops=dict(width=0.55))
ax.set_title("Equity Fund Portfolio — Sector Allocation by Market Value", fontsize=13, fontweight="bold")
plt.tight_layout(); save(fig, "09_sector_allocation.png")

# ── Chart 10: Fund House Scheme Count ─────────────────────────────────────
fh_counts = fund_master["fund_house"].value_counts()
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(fh_counts.index, fh_counts.values, color=plt.cm.Blues(np.linspace(0.4, 0.9, len(fh_counts))))
ax.bar_label(bars, padding=3); ax.set_title("Number of Schemes per Fund House", fontsize=13, fontweight="bold")
ax.set_xlabel("Schemes"); plt.tight_layout(); save(fig, "10_fund_house_dist.png")

# ── Chart 11: Risk Distribution ───────────────────────────────────────────
risk_counts = fund_master["risk_category"].value_counts()
fig, ax = plt.subplots(figsize=(8, 6))
ax.pie(risk_counts.values, labels=risk_counts.index, autopct="%1.1f%%", startangle=90, pctdistance=0.82,
    wedgeprops=dict(width=0.55))
ax.set_title("Fund Risk Grade Distribution", fontsize=13, fontweight="bold")
plt.tight_layout(); save(fig, "11_risk_distribution.png")

# ── Chart 12: Expense Ratio ───────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
sns.histplot(fund_master["expense_ratio_pct"], bins=15, kde=True, color="#5C6BC0", ax=ax, edgecolor="white")
ax.axvline(fund_master["expense_ratio_pct"].mean(), color="red", linestyle="--",
    label=f"Mean: {fund_master['expense_ratio_pct'].mean():.2f}%")
ax.axvline(1.0, color="orange", linestyle=":", label="1% Threshold")
ax.set_title("Expense Ratio Distribution Across All Schemes", fontsize=13, fontweight="bold")
ax.set_xlabel("Expense Ratio (%)"); ax.set_ylabel("Frequency"); ax.legend()
plt.tight_layout(); save(fig, "12_expense_ratio.png")

# ── Chart 13: Transaction Types ───────────────────────────────────────────
txn_type = transactions["transaction_type"].value_counts()
fig, ax = plt.subplots(figsize=(8, 6))
ax.pie(txn_type.values, labels=txn_type.index, autopct="%1.1f%%", startangle=90,
    colors=["#42A5F5","#66BB6A","#EF5350"], wedgeprops=dict(width=0.55))
ax.set_title("Investor Transaction Type Distribution", fontsize=13, fontweight="bold")
plt.tight_layout(); save(fig, "13_transaction_types.png")

# ── Chart 14: Risk-Return Scatter ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 7))
for cat, grp in performance.groupby("category"):
    ax.scatter(grp["sharpe_ratio"], grp["return_3yr_pct"], s=grp["aum_crore"]/100, alpha=0.7, label=cat)
ax.axhline(performance["return_3yr_pct"].mean(), linestyle=":", color="gray", label="Avg Return")
ax.axvline(1.0, linestyle=":", color="orange", label="Sharpe=1.0")
ax.set_title("Risk-Return Map — Sharpe Ratio vs 3-Year Return", fontsize=13, fontweight="bold")
ax.set_xlabel("Sharpe Ratio"); ax.set_ylabel("3-Yr CAGR (%)")
ax.legend(fontsize=8, loc="upper left"); plt.tight_layout(); save(fig, "14_risk_return_scatter.png")

# ── Chart 15: Monthly Transaction Trend ──────────────────────────────────
txn_monthly = (transactions.groupby(transactions["transaction_date"].dt.to_period("M"))
    .agg(count=("amount_inr","count"), total_cr=("amount_inr", lambda x: x.sum()/1e7)).reset_index())
txn_monthly["transaction_date"] = txn_monthly["transaction_date"].dt.to_timestamp()
fig, ax1 = plt.subplots(figsize=(14, 5))
ax2 = ax1.twinx()
ax1.bar(txn_monthly["transaction_date"], txn_monthly["count"], color="#90CAF9", alpha=0.8, label="Count")
ax2.plot(txn_monthly["transaction_date"], txn_monthly["total_cr"], color="#F4511E", lw=2.5, marker="o", ms=4, label="Value (₹Cr)")
ax1.set_title("Monthly Transaction Volume & Value Trend", fontsize=13, fontweight="bold")
ax1.set_ylabel("Count"); ax2.set_ylabel("Value (₹ Crore)")
ax1.legend(loc="upper left"); ax2.legend(loc="upper right")
plt.tight_layout(); save(fig, "15_monthly_transactions.png")

# ── Chart 16: Category Treemap ────────────────────────────────────────────
try:
    import squarify
    cat_dist = fund_master.groupby("category").size().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(12, 7))
    squarify.plot(sizes=cat_dist.values, label=cat_dist.index, alpha=0.8, ax=ax,
        color=plt.cm.viridis(np.linspace(0.2, 0.9, len(cat_dist))))
    ax.set_title("Fund Category Distribution Treemap", fontsize=13, fontweight="bold")
    ax.axis("off"); plt.tight_layout(); save(fig, "16_category_treemap.png")
except ImportError:
    # fallback bar chart if squarify not installed
    cat_dist = fund_master.groupby("category").size().sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(cat_dist.index, cat_dist.values, color="#7B1FA2")
    ax.set_title("Fund Category Distribution", fontsize=13, fontweight="bold")
    plt.tight_layout(); save(fig, "16_category_treemap.png")

# ── Chart 17: Benchmark Comparison ───────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 6))
for name, grp in benchmark.groupby("index_name"):
    ax.plot(grp["date"], grp["close_value"], lw=2, label=name)
ax.set_title("Benchmark Index Performance Comparison (2022–2026)", fontsize=13, fontweight="bold")
ax.set_xlabel("Date"); ax.set_ylabel("Index Value"); ax.legend()
plt.tight_layout(); save(fig, "17_benchmark_comparison.png")

# ── Chart 18: Top 10 Funds by AUM ────────────────────────────────────────
top10_aum = performance.nlargest(10, "aum_crore").copy()
top10_aum["short_name"] = top10_aum["scheme_name"].str.replace(r" - (Regular|Direct).*","",regex=True).str.slice(0,30)
top10_aum = top10_aum.sort_values("aum_crore")
fig, ax = plt.subplots(figsize=(12, 7))
colors = plt.cm.RdYlGn(np.linspace(0.2, 0.9, len(top10_aum)))
bars = ax.barh(top10_aum["short_name"], top10_aum["aum_crore"], color=colors)
ax.set_title("Top 10 Funds by AUM — Coloured by 3-Yr Return", fontsize=13, fontweight="bold")
ax.set_xlabel("AUM (₹ Crore)"); plt.tight_layout(); save(fig, "18_top10_aum.png")

print(f"\n✅ All 18 charts saved to: {CHARTS_DIR}")
