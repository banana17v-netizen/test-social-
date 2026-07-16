"""Local Streamlit dashboard to run and inspect the social-listening harness pipeline.

Presentation-only redesign: the pipeline call (`app.invoke`) and every field read from
`out` are unchanged from the original. All harness code under `harness/` is untouched.

Design system (see the `dataviz` skill): custom components are built with injected
HTML/CSS rather than stock Streamlit widgets so the whole page reads as one system and
adapts to Streamlit's Light/Dark theme. Surfaces are neutral translucent washes and text
is inherited (so both themes look right); only the *marks* carry the validated palette:

  - Status palette (fixed, never themed): ok=good, degraded=warning, down=critical.
    Always shown as dot + label, never colour alone.
  - Categorical palette for the 6 evidence types (validated for light & dark via
    scripts/validate_palette.js): exchange_flow=blue, funding_rate=green, social=magenta,
    whale=yellow, github=aqua, tvl=orange. Every bar/card is direct-labelled, which is the
    required relief for the sub-3:1 light-mode hues.
  - Confidence is a *meter* (single ratio vs a limit), rendered with a hatched/provisional
    fill and an explicit "(uncalibrated)" tag so it never reads like a backtested number.
"""
import html
import logging
import os

import streamlit as st

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


_load_dotenv()

from harness.contracts import UserProfile  # noqa: E402
from harness.graph import app  # noqa: E402

st.set_page_config(page_title="Social Listening Harness", page_icon="\U0001f4e1", layout="wide")

# --------------------------------------------------------------------------------------
# Palette / metadata
# --------------------------------------------------------------------------------------
# Categorical hues per evidence type — light + dark steps, validated by the dataviz
# palette validator (worst adjacent CVD dE 9.1 light / 8.4 dark; normal-vision floor
# 19.6 / 19.3). Icons aid 3-second recognition; the colour carries identity.
TYPE_META = {
    "exchange_flow": {"icon": "\U0001f504", "label": "Exchange flow", "light": "#2a78d6", "dark": "#3987e5"},
    "funding_rate":  {"icon": "\U0001f4b9", "label": "Funding rate",  "light": "#008300", "dark": "#008300"},
    "social":        {"icon": "\U0001f4ac", "label": "Social",        "light": "#e87ba4", "dark": "#d55181"},
    "whale":         {"icon": "\U0001f40b", "label": "Whale",         "light": "#eda100", "dark": "#c98500"},
    "github":        {"icon": "\U0001f419", "label": "GitHub",        "light": "#1baf7a", "dark": "#199e70"},
    "tvl":           {"icon": "\U0001f512", "label": "TVL",           "light": "#eb6834", "dark": "#d95926"},
}

# Health -> fixed status role (good / warning / critical). Never themed.
HEALTH_META = {
    "ok":       {"role": "ok",       "label": "ok"},
    "degraded": {"role": "degraded", "label": "degraded"},
    "down":     {"role": "down",     "label": "down"},
}

LIFECYCLE_STAGES = ["emerging", "strengthening", "peaking", "weakening", "dead"]


def esc(x):
    return html.escape(str(x))


def html_block(s):
    st.markdown(s, unsafe_allow_html=True)


# --------------------------------------------------------------------------------------
# CSS (one injected stylesheet — the whole design system)
# --------------------------------------------------------------------------------------
_BASE_CSS = """<style>
.block-container{padding-top:2.2rem;max-width:1180px;}
.sl-hero{margin:0 0 .35rem 0;}
.sl-hero h1{font-size:1.65rem;font-weight:700;letter-spacing:-.02em;margin:0;line-height:1.15;}
.sl-hero p{margin:.3rem 0 0 0;font-size:.9rem;opacity:.6;}
.sl-sec{display:flex;align-items:center;gap:.6rem;margin:1.9rem 0 .85rem 0;}
.sl-sec .t{font-size:.72rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;opacity:.55;white-space:nowrap;}
.sl-sec .r{height:1px;flex:1;background:rgba(128,128,128,.22);}
/* KPI row -------------------------------------------------------------------------- */
.sl-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;}
.sl-kpi{background:rgba(128,128,128,.06);border:1px solid rgba(128,128,128,.20);border-radius:14px;padding:14px 16px;position:relative;overflow:hidden;}
.sl-kpi .k{font-size:.68rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.5;}
.sl-kpi .v{font-size:1.5rem;font-weight:700;letter-spacing:-.01em;margin-top:.25rem;line-height:1.1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.sl-kpi .s{font-size:.78rem;opacity:.6;margin-top:.28rem;}
.sl-kpi.accent{border-color:color-mix(in srgb,var(--a) 45%,transparent);background:color-mix(in srgb,var(--a) 9%,rgba(128,128,128,.05));}
.sl-kpi.accent::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--a);}
.sl-kpi.accent .v{color:var(--a);}
/* Pills / status ------------------------------------------------------------------- */
.sl-pill{display:inline-flex;align-items:center;gap:.4rem;font-size:.78rem;font-weight:600;padding:.28rem .6rem;border-radius:999px;border:1px solid color-mix(in srgb,var(--s) 38%,transparent);background:color-mix(in srgb,var(--s) 13%,transparent);}
.sl-pill .dot{width:9px;height:9px;border-radius:50%;background:var(--s);flex:none;box-shadow:0 0 0 3px color-mix(in srgb,var(--s) 22%,transparent);}
.sl-pill .nm{opacity:.95;}
.sl-pill .st{opacity:.6;font-weight:600;}
.sl-healthrow{display:flex;flex-wrap:wrap;gap:12px;}
.sl-st-ok{--s:#0ca30c;} .sl-st-degraded{--s:#fab219;} .sl-st-down{--s:#d03b3b;}
/* Verification banner --------------------------------------------------------------- */
.sl-banner{border-radius:14px;padding:16px 18px;display:flex;gap:14px;align-items:flex-start;}
.sl-banner .ic{font-size:1.35rem;line-height:1;flex:none;margin-top:.05rem;}
.sl-banner .bt{font-weight:700;letter-spacing:.01em;}
.sl-banner .bd{font-size:.86rem;opacity:.85;margin-top:.25rem;}
.sl-banner ul{margin:.45rem 0 0 0;padding-left:1.05rem;font-size:.84rem;opacity:.9;}
.sl-banner li{margin:.12rem 0;}
.sl-banner.fail{background:color-mix(in srgb,#d03b3b 13%,transparent);border:1px solid color-mix(in srgb,#d03b3b 45%,transparent);border-left:5px solid #d03b3b;}
.sl-banner.fail .bt{color:#d03b3b;font-size:1.02rem;text-transform:uppercase;letter-spacing:.05em;}
.sl-banner.pass{background:color-mix(in srgb,#0ca30c 10%,transparent);border:1px solid color-mix(in srgb,#0ca30c 34%,transparent);border-left:5px solid #0ca30c;padding:11px 16px;}
.sl-banner.pass .bt{color:#0a8a0a;font-size:.9rem;}
/* Confidence meter ------------------------------------------------------------------ */
.sl-meter{background:rgba(128,128,128,.06);border:1px solid rgba(128,128,128,.20);border-radius:14px;padding:16px 18px;}
.sl-meter .top{display:flex;align-items:baseline;gap:.8rem;flex-wrap:wrap;}
.sl-meter .num{font-size:3rem;font-weight:700;letter-spacing:-.02em;line-height:1;color:#2a78d6;}
.sl-meter .uncal{--s:#fab219;display:inline-flex;align-items:center;gap:.35rem;font-size:.72rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:.22rem .55rem;border-radius:999px;border:1px solid color-mix(in srgb,var(--s) 45%,transparent);background:color-mix(in srgb,var(--s) 15%,transparent);}
.sl-meter .uncal .dot{width:8px;height:8px;border-radius:50%;background:var(--s);}
.sl-meter .track{position:relative;height:14px;border-radius:999px;background:rgba(128,128,128,.16);margin:14px 0 6px 0;overflow:hidden;}
.sl-meter .fill{position:absolute;left:0;top:0;bottom:0;border-radius:999px;background-image:repeating-linear-gradient(135deg,rgba(255,255,255,.42) 0 5px,transparent 5px 9px),linear-gradient(90deg,#86b6ef,#2a78d6);}
.sl-meter .ticks{display:flex;justify-content:space-between;font-size:.68rem;opacity:.45;font-variant-numeric:tabular-nums;}
.sl-meter .cap{font-size:.8rem;opacity:.6;margin-top:.55rem;}
/* Narrative ------------------------------------------------------------------------- */
.sl-narr{background:rgba(128,128,128,.06);border:1px solid rgba(128,128,128,.20);border-radius:14px;padding:16px 18px;}
.sl-narr .nm{font-size:1.18rem;font-weight:700;letter-spacing:-.01em;}
.sl-narr .rs{font-size:.88rem;opacity:.72;margin-top:.5rem;line-height:1.5;}
.sl-life{display:flex;gap:6px;margin-top:.9rem;}
.sl-life .stg{flex:1;text-align:center;font-size:.66rem;font-weight:600;letter-spacing:.02em;padding:.42rem .2rem;border-radius:8px;background:rgba(128,128,128,.10);opacity:.55;text-transform:capitalize;}
.sl-life .stg.done{background:color-mix(in srgb,#2a78d6 16%,transparent);opacity:.85;}
.sl-life .stg.now{background:#2a78d6;color:#fff;opacity:1;box-shadow:0 2px 8px color-mix(in srgb,#2a78d6 40%,transparent);}
/* Attribution bars ------------------------------------------------------------------ */
.sl-attr{background:rgba(128,128,128,.06);border:1px solid rgba(128,128,128,.20);border-radius:14px;padding:16px 18px;}
.sl-attr .exp{font-size:.92rem;line-height:1.55;}
.sl-legend{display:flex;flex-wrap:wrap;gap:12px;margin:.9rem 0 .3rem 0;}
.sl-legend .li{display:inline-flex;align-items:center;gap:.4rem;font-size:.76rem;opacity:.8;}
.sl-legend .sw{width:11px;height:11px;border-radius:3px;background:var(--c);}
.sl-bars{margin-top:.6rem;display:flex;flex-direction:column;gap:11px;}
.sl-bar .lab{display:flex;justify-content:space-between;gap:1rem;font-size:.82rem;margin-bottom:.28rem;}
.sl-bar .lab .w{font-weight:700;font-variant-numeric:tabular-nums;opacity:.9;}
.sl-bar .track{height:12px;border-radius:999px;background:rgba(128,128,128,.14);overflow:hidden;}
.sl-bar .fill{height:100%;border-radius:999px;background:var(--c);min-width:4px;transition:width .3s ease;}
/* Evidence cards -------------------------------------------------------------------- */
.sl-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;}
.sl-card{background:rgba(128,128,128,.06);border:1px solid rgba(128,128,128,.20);border-left:4px solid var(--c);border-radius:12px;padding:13px 15px;display:flex;flex-direction:column;gap:.5rem;}
.sl-card .hd{display:flex;align-items:center;gap:.55rem;}
.sl-card .chip{width:30px;height:30px;flex:none;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:1rem;background:color-mix(in srgb,var(--c) 16%,transparent);border:1px solid color-mix(in srgb,var(--c) 34%,transparent);}
.sl-card .ty{font-size:.72rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--c);}
.sl-card .mag{margin-left:auto;font-size:.78rem;font-weight:700;font-variant-numeric:tabular-nums;opacity:.85;}
.sl-card .sum{font-size:.86rem;line-height:1.45;opacity:.9;}
.sl-card .mbar{height:6px;border-radius:999px;background:rgba(128,128,128,.14);overflow:hidden;}
.sl-card .mbar>i{display:block;height:100%;border-radius:999px;background:var(--c);opacity:.85;}
/* Empty / error --------------------------------------------------------------------- */
.sl-empty{text-align:center;padding:34px 18px;border:1px dashed rgba(128,128,128,.35);border-radius:14px;background:rgba(128,128,128,.04);}
.sl-empty .em{font-size:1.6rem;opacity:.5;}
.sl-empty .t{font-weight:600;margin-top:.4rem;opacity:.8;}
.sl-empty .d{font-size:.84rem;opacity:.55;margin-top:.25rem;}
.sl-err{background:color-mix(in srgb,#d03b3b 12%,transparent);border:1px solid color-mix(in srgb,#d03b3b 42%,transparent);border-left:5px solid #d03b3b;border-radius:14px;padding:16px 18px;}
.sl-err .t{font-weight:700;color:#d03b3b;display:flex;align-items:center;gap:.5rem;}
.sl-err pre{margin:.6rem 0 0 0;font-size:.8rem;white-space:pre-wrap;opacity:.85;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}
.sl-idle{text-align:center;padding:46px 18px;border:1px dashed rgba(128,128,128,.30);border-radius:16px;background:rgba(128,128,128,.04);}
.sl-idle .em{font-size:2rem;opacity:.5;}
.sl-idle .t{font-weight:600;margin-top:.5rem;font-size:1.02rem;}
.sl-idle .d{font-size:.86rem;opacity:.55;margin-top:.3rem;}
</style>"""


def _type_theme_css():
    light = "".join(f'.sl-c-{t}{{--c:{m["light"]};}}' for t, m in TYPE_META.items())
    dark = "".join(f'.sl-c-{t}{{--c:{m["dark"]};}}' for t, m in TYPE_META.items())
    return (
        "<style>" + light
        + "@media (prefers-color-scheme:dark){"
        + dark
        + ".sl-meter .num{color:#3987e5;}.sl-meter .fill{background-image:repeating-linear-gradient(135deg,rgba(255,255,255,.22) 0 5px,transparent 5px 9px),linear-gradient(90deg,#1c5cab,#3987e5);}"
        + ".sl-life .stg.now{color:#0d0d0d;}.sl-banner.pass .bt{color:#2fbf4a;}"
        + "}</style>"
    )


def inject_css():
    html_block(_BASE_CSS)
    html_block(_type_theme_css())


def section(title):
    html_block(f'<div class="sl-sec"><span class="t">{esc(title)}</span><span class="r"></span></div>')


# --------------------------------------------------------------------------------------
# Component renderers
# --------------------------------------------------------------------------------------
def render_kpis(token, narrative, conf, verification):
    conf_txt = "—" if conf is None else f"{conf:.0%}"
    if narrative:
        narr_v = esc(narrative.narrative_name)
        narr_s = f"lifecycle: {esc(narrative.lifecycle_stage)}"
    else:
        narr_v, narr_s = "—", "not classified"
    if verification is None:
        ver_a, ver_v, ver_s = "#898781", "n/a", "not run"
    elif verification.passed:
        ver_a, ver_v, ver_s = "#0ca30c", "Passed", "grounded in evidence"
    else:
        ver_a, ver_v, ver_s = "#d03b3b", "Failed", "fallback template used"
    html_block(
        '<div class="sl-kpis">'
        f'<div class="sl-kpi"><div class="k">Token</div><div class="v">{esc(token)}</div><div class="s">signal snapshot</div></div>'
        f'<div class="sl-kpi"><div class="k">Narrative</div><div class="v" title="{narr_v}">{narr_v}</div><div class="s">{narr_s}</div></div>'
        f'<div class="sl-kpi"><div class="k">Confidence</div><div class="v" style="color:#2a78d6">{conf_txt}</div><div class="s">uncalibrated</div></div>'
        f'<div class="sl-kpi accent" style="--a:{ver_a}"><div class="k">Verification</div><div class="v">{ver_v}</div><div class="s">{ver_s}</div></div>'
        '</div>'
    )


def render_verification_banner(v):
    if v is None:
        return
    if v.passed:
        html_block(
            '<div class="sl-banner pass"><div class="ic">✅</div><div>'
            '<div class="bt">Verification passed</div>'
            '<div class="bd">Attribution is grounded in collected evidence.</div>'
            '</div></div>'
        )
    else:
        probs = "".join(f"<li>{esc(p)}</li>" for p in (v.problems or [])) or "<li>(no detail provided)</li>"
        html_block(
            '<div class="sl-banner fail"><div class="ic">⛔</div><div>'
            '<div class="bt">Verification failed — fallback template in use</div>'
            '<div class="bd">The generated attribution was not grounded in evidence, so a safe fallback was substituted. Treat this output with caution.</div>'
            f'<ul>{probs}</ul>'
            '</div></div>'
        )


def render_health(raw_data):
    if not raw_data:
        html_block('<div class="sl-empty"><div class="em">\U0001f4e1</div><div class="t">No data-source telemetry</div></div>')
        return
    pills = []
    for row in raw_data:
        health = row.get("source_health", "down")
        meta = HEALTH_META.get(health, HEALTH_META["down"])
        pills.append(
            f'<span class="sl-pill sl-st-{meta["role"]}"><span class="dot"></span>'
            f'<span class="nm">{esc(row.get("source", "?"))}</span>'
            f'<span class="st">· {esc(meta["label"])}</span></span>'
        )
    html_block('<div class="sl-healthrow">' + "".join(pills) + '</div>')


def render_confidence(conf):
    if conf is None:
        html_block(
            '<div class="sl-meter">'
            '<div class="top"><span class="num" style="opacity:.4">—</span>'
            '<span class="uncal"><span class="dot"></span>uncalibrated</span></div>'
            '<div class="cap">Confidence not available for this run.</div>'
            '</div>'
        )
        return
    v = max(0.0, min(1.0, float(conf)))
    pct = f"{v:.0%}"
    html_block(
        '<div class="sl-meter">'
        f'<div class="top"><span class="num">{pct}</span>'
        '<span class="uncal"><span class="dot"></span>uncalibrated</span></div>'
        f'<div class="track"><div class="fill" style="width:{v * 100:.1f}%"></div></div>'
        '<div class="ticks"><span>0</span><span>25</span><span>50</span><span>75</span><span>100</span></div>'
        '<div class="cap">No golden-set backtest yet — read this as a rough prior, not a calibrated probability.</div>'
        '</div>'
    )


def render_narrative(n):
    if not n:
        return
    stage = n.lifecycle_stage
    idx = LIFECYCLE_STAGES.index(stage) if stage in LIFECYCLE_STAGES else -1
    segs = []
    for i, s in enumerate(LIFECYCLE_STAGES):
        cls = "now" if i == idx else ("done" if -1 < idx and i < idx else "")
        segs.append(f'<span class="stg {cls}">{esc(s)}</span>')
    html_block(
        '<div class="sl-narr">'
        f'<div class="nm">{esc(n.narrative_name)}</div>'
        f'<div class="rs">{esc(n.reasoning)}</div>'
        '<div class="sl-life">' + "".join(segs) + '</div>'
        '</div>'
    )


def render_attribution(attr, type_by_id):
    if not attr:
        return
    factors = list(attr.contributing_factors or [])
    factors.sort(key=lambda f: f.attribution_weight, reverse=True)
    max_w = max((f.attribution_weight for f in factors), default=0.0) or 1.0

    seen_types = []
    for f in factors:
        t = type_by_id.get(f.evidence_id)
        if t and t not in seen_types:
            seen_types.append(t)
    legend = "".join(
        f'<span class="li"><span class="sw sl-c-{t}"></span>{esc(TYPE_META[t]["label"])}</span>'
        for t in seen_types
    )

    bars = []
    for f in factors:
        t = type_by_id.get(f.evidence_id)
        cls = f"sl-c-{t}" if t else ""
        w = max(0.0, min(1.0, f.attribution_weight))
        width = (f.attribution_weight / max_w) * 100 if max_w else 0
        width = max(0.0, min(100.0, width))
        tt = TYPE_META[t]["label"] if t else "unattributed"
        min_w = 4 if width > 0 else 0
        bars.append(
            f'<div class="sl-bar {cls}" title="{esc(f.label)} — {tt} — {w:.0%}">'
            f'<div class="lab"><span>{esc(f.label)}</span><span class="w">{w:.0%}</span></div>'
            f'<div class="track"><div class="fill" style="width:{width:.1f}%;min-width:{min_w}px"></div></div></div>'
        )
    body = '<div class="sl-bars">' + "".join(bars) + '</div>' if bars else '<div class="cap">No contributing factors.</div>'
    legend_html = f'<div class="sl-legend">{legend}</div>' if legend else ""
    html_block(
        '<div class="sl-attr">'
        f'<div class="exp">{esc(attr.explanation_text)}</div>'
        f'{legend_html}{body}'
        f'<div class="sl-meter" style="border:0;background:none;padding:0;"><div class="cap" style="margin-top:.7rem;">⚠️ {esc(attr.caveat)}</div></div>'
        '</div>'
    )


def render_evidence(bundle):
    if not (bundle and bundle.items):
        html_block(
            '<div class="sl-empty"><div class="em">\U0001f4ed</div>'
            '<div class="t">No evidence collected</div>'
            '<div class="d">All sources may be down — check data-source health above.</div></div>'
        )
        return
    items = sorted(bundle.items, key=lambda e: abs(e.magnitude), reverse=True)
    max_m = max((abs(e.magnitude) for e in items), default=0.0) or 1.0
    cards = []
    for e in items:
        meta = TYPE_META.get(e.type, {"icon": "•", "label": e.type})
        cls = f"sl-c-{e.type}" if e.type in TYPE_META else ""
        mbar = max(0.0, min(100.0, abs(e.magnitude) / max_m * 100))
        cards.append(
            f'<div class="sl-card {cls}">'
            f'<div class="hd"><span class="chip">{meta["icon"]}</span>'
            f'<span class="ty">{esc(meta["label"])}</span>'
            f'<span class="mag">{e.magnitude:.2f}</span></div>'
            f'<div class="sum">{esc(e.summary)}</div>'
            f'<div class="mbar"><i style="width:{mbar:.1f}%"></i></div>'
            '</div>'
        )
    html_block('<div class="sl-cards">' + "".join(cards) + '</div>')


# --------------------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------------------
inject_css()
html_block(
    '<div class="sl-hero"><h1>\U0001f4e1 Social Listening Harness</h1>'
    '<p>Runs the real LangGraph pipeline — live tools + live Gemini calls. No mocks.</p></div>'
)

with st.sidebar:
    st.markdown("### Input")
    token = st.text_input("Token symbol", value="ETH").strip().upper()
    st.markdown("")
    risk = st.selectbox("Risk appetite", ["conservative", "moderate", "aggressive"], index=1)
    horizon = st.selectbox("Time horizon", ["intraday", "swing", "long"], index=1)
    watchlist_raw = st.text_input("Watchlist (comma-separated)", value=token)
    st.markdown("")
    run_btn = st.button("Run pipeline", type="primary", use_container_width=True)

if run_btn:
    if not token:
        st.error("Enter a token symbol first.")
        st.stop()

    profile = UserProfile(
        holdings=[],
        watchlist=[t.strip().upper() for t in watchlist_raw.split(",") if t.strip()],
        risk_appetite=risk,
        time_horizon=horizon,
    )

    with st.spinner(f"Running pipeline for {token}..."):
        try:
            out = app.invoke({"token_symbol": token, "user_profile": profile})
        except Exception as e:
            html_block(
                '<div class="sl-err"><div class="t">⛔ Pipeline crashed</div>'
                f'<pre>{esc(type(e).__name__)}: {esc(e)}</pre></div>'
            )
            st.stop()

    verification = out.get("verification")
    narrative = out.get("narrative")
    attribution = out.get("attribution")
    bundle = out.get("bundle")
    conf = out.get("confidence")

    # 1) At-a-glance KPI row + the safety-critical verification banner (most prominent).
    section("Signal overview")
    render_kpis(token, narrative, conf, verification)
    st.markdown("")
    render_verification_banner(verification)

    # 2) Data-source health.
    section("Data sources")
    render_health(out.get("raw_data", []))

    # 3) Confidence meter.
    section("Confidence")
    render_confidence(conf)

    # 4) Narrative.
    if narrative:
        section("Narrative")
        render_narrative(narrative)

    # 5) Attribution — map each factor's evidence_id to its evidence type for colour.
    type_by_id = {}
    if bundle and bundle.items:
        type_by_id = {e.evidence_id: e.type for e in bundle.items}
    if attribution:
        section("Attribution")
        render_attribution(attribution, type_by_id)

    # 6) Evidence.
    section(f"Evidence ({len(bundle.items) if (bundle and bundle.items) else 0})")
    render_evidence(bundle)

    # 7) Raw feed item(s) — tucked into an expander to keep the page clean.
    feed_items = out.get("feed_items", [])
    if feed_items:
        section("Raw output")
        with st.expander(f"Feed item{'s' if len(feed_items) > 1 else ''} (final JSON)"):
            for fi in feed_items:
                st.json(fi.model_dump(mode="json"))

    # 8) Errors.
    if out.get("errors"):
        section("Errors")
        html_block(
            '<div class="sl-err"><div class="t">⚠️ Pipeline reported errors</div>'
            f'<pre>{esc(chr(10).join(out["errors"]))}</pre></div>'
        )
else:
    html_block(
        '<div class="sl-idle"><div class="em">\U0001f9ed</div>'
        '<div class="t">Ready to run</div>'
        '<div class="d">Enter a token symbol on the left and click <b>Run pipeline</b>.</div></div>'
    )