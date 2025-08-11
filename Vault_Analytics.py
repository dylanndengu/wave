# app.py
try:
    import plotly.express as px
    import streamlit as st
    import pandas as pd
    
except ImportError:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly>=5.24"])
    import plotly.express as px
    import streamlit as st
    import pandas as pd



st.set_page_config(page_title="Vault Analytics", layout="centered")
st.title("🔐 Vault Analytics")

CSV_PATH1 = r"lock_duration.csv" 
CSV_PATH2 = r"early_unlocks.csv"
CSV_PATH3 = r"lock_duration_with_early_unlock.csv"
CSV_PATH4 = r"adoption rate_excl.csv"
CSV_PATH5 = r"hour_of_contact.csv"
CSV_PATH6 = r"early unlock.csv"

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

locks_df = load_data(CSV_PATH1)
early_df = load_data(CSV_PATH2)
lock_with_early_df = load_data(CSV_PATH3)
adoption_df = load_data(CSV_PATH4)

# ------------------------
# Chart 1 — Lock durations
# ------------------------
locks_df["share"] = locks_df["locks"] / locks_df["locks"].sum()
lock_order = [
    ">101 days", "90–101 days", "60–89 days", "30–59 days",
    "14–29 days", "7–13 days", "1–6 days", "<1 day"
]
locks_df["bucket"] = pd.Categorical(locks_df["bucket"], lock_order, ordered=True)

# Use the same (sorted) dataframe for plotting AND labels
plot_df = locks_df.sort_values("bucket").reset_index(drop=True)

fig_locks = px.bar(
    plot_df,
    x="share", y="bucket", orientation="h",
    labels={"share": "Share of locks", "bucket": "Lock duration"},
    title="Distribution of Lock Durations"
)

# Make labels come from the bar's x value so they always match
fig_locks.update_traces(
    text=plot_df["share"],
    texttemplate="%{text:.1%}",
    textposition="outside",   # or "inside" if you prefer
    marker_line_width=0
)

fig_locks.update_layout(xaxis_tickformat=".0%", yaxis_title="Buckets")
st.plotly_chart(fig_locks, use_container_width=True)

top = locks_df.sort_values("share", ascending=False).head(3).reset_index(drop=True)
b1, b2, b3 = top.loc[0], top.loc[1], top.loc[2]

summary_text = (
    f"Most popular lock duration is **{b1['bucket']}** at **{b1['share']:.0%}**, "
    f"followed by **{b2['bucket']}** (**{b2['share']:.0%}**) and **{b3['bucket']}** (**{b3['share']:.0%}**)."
)
st.markdown(summary_text)

# ------------------------
# Chart 2 — Early unlocks
# ------------------------
# Early unlocks — fixed labels
early_df["share"] = early_df["unlocks"] / early_df["unlocks"].sum()

early_order = [
    "<1 day early", "1–6 days early", "7–13 days early",
    "14–29 days early", "30–59 days early", "60–89 days early", "≥90 days early"
]
early_df["bucket"] = pd.Categorical(early_df["bucket"], early_order, ordered=True)

# Use one sorted df for plot + labels
plot_df = early_df.sort_values("bucket").reset_index(drop=True)

fig_early = px.bar(
    plot_df,
    x="share", y="bucket", orientation="h",
    labels={"share": "Share of early unlocks", "bucket": "Days early"},
    title="How Often Customers Unlock Before the Due Date"
)

# Labels pulled from the plotted x values so they always align
fig_early.update_traces(
    text=plot_df["share"],
    texttemplate="%{text:.1%}",
    textposition="outside",
    marker_line_width=0
)

fig_early.update_layout(xaxis_tickformat=".0%", yaxis_title="Buckets")
st.plotly_chart(fig_early, use_container_width=True)

st.markdown(
    "**Summary:** Most early unlocks happen in the **final month before the scheduled unlock date** — about "
    "**70%** occur **1–29 days before due date** (1–6 days ~**29%**, 7–13 days ~**17%**, 14–29 days ~**24%**). "
    "Roughly **17%** occur **30–59 days** before. **Very-early** unlocks (≥60 days before) make up about **13%** "
    "(≥90 days ~**10%**, 60–89 days ~**2%**). Unlocks **<1 day** before due are negligible (**0.1%**)."
    "\n\n"
    "**Action:** Have a **partial withdraw allowance** in the last **30 days** before the timed unlock so users can access a small portion without fully unlocking."
)

# ------------------------
# Chart 3 — Early unlocks
# ------------------------
lock_with_early_df["not_early_count"] = (
    lock_with_early_df["locks"] - lock_with_early_df["early_unlocks"]
)

long = (
    lock_with_early_df.melt(
        id_vars=["bucket"],
        value_vars=["not_early_count", "early_unlocks"],
        var_name="status",
        value_name="count"
    )
    .replace({"not_early_count": "Not unlocked early",
              "early_unlocks": "Unlocked early"})
)

totals = long.groupby("bucket", as_index=False)["count"].sum().rename(columns={"count": "total"})
long = long.merge(totals, on="bucket", how="left")
long["pct"] = long["count"] / long["total"]
long["pct_label"] = (100 * long["pct"]).round(1).astype(str) + "%"

bucket_order = ["<1 day", "1–6 days", "7–13 days", "14–29 days",
    "30–59 days", "60–89 days", "90–101 days", ">101 days"]

fig = px.bar(
    long.sort_values(["bucket", "status"]),
    x="pct", y="bucket", color="status", orientation="h",
    text="pct_label",  # <- use the column, not a separate array
    labels={"pct": "Share of locks", "bucket": "Lock duration", "status": ""},
    title="Percentage Unlocked Early per Bucket",
    category_orders={"bucket": bucket_order,
                     "status": ["Not unlocked early", "Unlocked early"]},
    color_discrete_map={"Not unlocked early": "#1f77b4",
                        "Unlocked early": "#FFD23F"}
)

fig.update_layout(barmode="stack", xaxis_tickformat=".0%", xaxis_range=[0, 1],
                  yaxis_title=None, legend_traceorder="reversed")
fig.update_traces(marker_line_width=0)

st.plotly_chart(fig, use_container_width=True)


tmp = lock_with_early_df.copy()
tmp["early_rate"] = tmp["early_unlocks"] / tmp["locks"]
tmp = tmp.set_index("bucket")

def r(b):
    return float(tmp.loc[b, "early_rate"]) if b in tmp.index else float("nan")

overall = (lock_with_early_df["early_unlocks"].sum() / lock_with_early_df["locks"].sum())

summary_text = (
    f"**Summary:** Overall, **{overall:.0%}** of locks are unlocked early. "
    f"Rates are highest for shorter locks — **<1 day {r('<1 day'):.1%}**, "
    f"**1–6 days {r('1–6 days'):.1%}**, **7–13 days {r('7–13 days'):.1%}** — "
    f"and moderate for longer durations: **14–29 days {r('14–29 days'):.1%}**, "
    f"**30–59 days {r('30–59 days'):.1%}**, **60–89 days {r('60–89 days'):.1%}**, "
    f"**90–101 days {r('90–101 days'):.1%}**, **>101 days {r('>101 days'):.1%}**."
)
st.markdown(summary_text)

st.markdown(
    "**Actions:**\n"
    "- Allow **partial withdrawals** with a fee if it is **before 14 days**.\n"
    "- Send **auto reminders** to customers with **more than a 2-week window** about alternatives to early unlocking.\n"
    "- **Incentivise** customers with a **period 14 days or longer** to keep funds in the vault via promotion campaigns."
)

# ------------------------
# Chart 4 — Adoption over time
# ------------------------

adopt = adoption_df.copy()
adopt.columns = adopt.columns.str.strip()
adopt = adopt.rename(columns={
    "LOCK_UNLOCK_INITIATOR": "initiator",
    "STATE": "state",
    "num_of_unlocks": "count"
})
adopt["period"] = pd.to_datetime(adopt["period"], errors="coerce")
adopt["pct"] = pd.to_numeric(adopt["pct"], errors="coerce")
adopt = adopt[adopt["state"].str.upper() == "UNLOCKED"]

adopt_no_time = adopt[adopt["initiator"].str.upper() != "TIME"]

adopt["pct_frac"] = adopt["pct"]
fig_adopt_share_ts = px.line(
    adopt.sort_values("period"),
    x="period", y="pct_frac", color="initiator", markers=True,
    text=((adopt.sort_values("period")["pct"] * 100).round(1).astype(str) + "%")
)
fig_adopt_share_ts.update_traces(textposition="top center")
fig_adopt_share_ts.update_yaxes(tickformat=".0%", range=[0, 1])

fig_adopt_share_ts.update_layout(
    title="Adoption Share by Initiator",
    xaxis_title="Period",
    yaxis_title="Share of Unlocks"
)

st.plotly_chart(fig_adopt_share_ts, use_container_width=True)

##Summary

adopt2 = adopt.copy()
# Handle either IVR spelling
adopt2["initiator"] = adopt2["initiator"].replace(
    {"INTERACTIVE_VOICE_RESPONSE": "IVR"}
)

# Latest period snapshot
latest = adopt2["period"].max()
latest_df = adopt2[adopt2["period"] == latest]
share = latest_df.groupby("initiator")["pct_frac"].sum()

support = float(share.get("SUPPORT", 0))
chatbot = float(share.get("CHATBOT", 0))
ivr = float(share.get("IVR", 0))
customer = float(share.get("CUSTOMER", 0))
self_serve = chatbot + ivr
total_latest = int(latest_df["count"].sum()) if "count" in latest_df.columns else None

# Previous period (for MoM deltas), if available
prev_periods = adopt2.loc[adopt2["period"] < latest, "period"]
prev = prev_periods.max() if not prev_periods.empty else None
selfserve_delta = support_delta = None
if prev is not None:
    prev_share = (
        adopt2[adopt2["period"] == prev]
        .groupby("initiator")["pct_frac"].sum()
    )
    prev_self = float(prev_share.get("CHATBOT", 0)) + float(prev_share.get("IVR", 0))
    selfserve_delta = self_serve - prev_self
    support_delta = support - float(prev_share.get("SUPPORT", 0))

# Summary
st.markdown(
    f"**Summary ({latest:%Y-%m}):** Self-serve (Chatbot + IVR) **{self_serve:.0%}**"
    f"{f' ({selfserve_delta:+.1%} MoM)' if selfserve_delta is not None else ''}, "
    f"Support **{support:.0%}**"
    f"{f' ({support_delta:+.1%} MoM)' if support_delta is not None else ''}, "
    f"Customer **{customer:.0%}**."
    + (f" Total unlocks **{total_latest:,}**." if total_latest is not None else "")
)

# Action point
st.markdown(
    "**Action:** Make self-serve the default **Unlock** CTA—route users to Chatbot/IVR first and keep Support as fallback. "
    "Set a short-term target of **≥75% self-serve share** and monitor completion rate and CSAT to ensure quality."
)



# ------------------------
# Chart 5 — Hour of support contacts
# ------------------------

hours_df = load_data(CSV_PATH5)

# Compute cumulative fraction (0–1) from the counts
total = hours_df["support_unlocks"].sum()
hours_df["cum_frac"] = hours_df["support_unlocks"].cumsum() / total

# Plot
fig = px.line(
    hours_df,
    x="hour_of_day",
    y="cum_frac",
    markers=True,
    labels={"hour_of_day": "Hour of day", "cum_frac": "Cumulative share"},
    title="Cumulative share of Support-initiated unlocks by hour"
)

fig.update_layout(yaxis_tickformat=".0%", yaxis_range=[0, 1])
st.plotly_chart(fig, use_container_width=True)


# df_hour: DataFrame with columns ['hour', 'count'] for SUPPORT unlocks
coverage = (df_hour.query("10 <= hour < 18")["count"].sum() / df_hour["count"].sum())

st.markdown(
    f"**Summary:** Support-initiated unlocks are concentrated in daytime hours. "
    f"The **10:00–18:00** window accounts for **{coverage:.0%}** of all support unlocks.\n\n"
    "**Action:** Limit live support for vault unlocks to **10:00–18:00** and route off-hours requests to self-serve (Chatbot/IVR) with an emergency fallback."
)


# ------------------------
# Chart 6 — Repeat offenders
# ------------------------

early_unlock_df = load_data(CSV_PATH6)
df = early_unlock_df.copy()
df.columns = df.columns.str.strip()
df["period"] = pd.to_datetime(df["period"], errors="coerce")
if "cohort" not in df.columns:
    df["cohort"] = "All"

# Build a 0–1 fraction for plotting
if "pct_early_after_frac" in df.columns:
    df["pct_frac"] = pd.to_numeric(df["pct_early_after_frac"], errors="coerce")
elif "pct_early_after" in df.columns:
    x = pd.to_numeric(df["pct_early_after"], errors="coerce")
    df["pct_frac"] = np.where(x > 1, x / 100.0, x)
else:
    df["pct_frac"] = (
        pd.to_numeric(df.get("early_unlocks_after"), errors="coerce")
        / pd.to_numeric(df.get("total_subsequent_sessions"), errors="coerce").replace(0, np.nan)
    )

# Label EVERY point
df["label"] = (df["pct_frac"] * 100).round(1).astype(str) + "%"

df = df.sort_values(["cohort", "period"])
fig = px.line(
    df,
    x="period",
    y="pct_frac",
    color="cohort",
    markers=True,
    text="label",
    labels={"period": "Month", "pct_frac": "Percent unlocking early next time", "cohort": ""}
)
fig.update_traces(textposition="top center", textfont_size=10)
fig.update_yaxes(tickformat=".0%", range=[0, 1])
fig.update_layout(title="Likelihood of Next Early Unlock — by Cohort (Monthly)")



st.plotly_chart(fig, use_container_width=True)


















