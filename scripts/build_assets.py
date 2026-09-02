#!/usr/bin/env python3
"""生成个人主页所需的全部 SVG 资产（亮/暗双主题）。

设计系统 "Circuit Aurora"：一份模板 + 两套配色变量，
避免亮暗主题各写一遍导致的视觉漂移。

用法：
    python3 scripts/build_assets.py            # 全部重建（stats 走 GitHub API）
    python3 scripts/build_assets.py --offline  # 跳过 API，stats 用缓存/占位值
"""
from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

USERNAME = os.environ.get("PROFILE_USERNAME", "bestxiangest")
ASSETS = Path("assets")
CACHE = ASSETS / ".stats-cache.json"
API_ROOT = "https://api.github.com"

# ---------------------------------------------------------------- 设计令牌

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg0": "#0a0e14",
        "bg1": "#0d131c",
        "surface": "#121b26",
        "line": "#1f2c3b",
        "grid": "#1a2734",
        "wire": "#2f4459",
        "text": "#e8eef5",
        "dim": "#93a1b1",
        "faint": "#5b6b7c",
        "cyan": "#45d9e8",
        "indigo": "#8aa4ff",
        "mint": "#4ade9b",
        "amber": "#ffc14d",
        "glow": "0.30",
        "gridop": "0.55",
    },
    "light": {
        "bg0": "#ffffff",
        "bg1": "#fbfdff",
        "surface": "#ffffff",
        "line": "#dde6f0",
        "grid": "#e6eef6",
        "wire": "#bfd2e4",
        "text": "#0d1a2b",
        "dim": "#4d5b6d",
        "faint": "#8290a1",
        "cyan": "#0d97ad",
        "indigo": "#4d61d0",
        "mint": "#0f8f65",
        "amber": "#bf7c08",
        "glow": "0.16",
        "gridop": "1",
    },
}

FONT = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, '
    '"PingFang SC", "Microsoft YaHei", sans-serif'
)
MONO = 'ui-monospace, SFMono-Regular, "JetBrains Mono", Consolas, monospace'


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def write(name: str, body: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_text(body, encoding="utf-8")
    print(f"  · assets/{name}")


# ---------------------------------------------------------------- 主横幅

# 「一个想法 → 分叉 → 多个能跑的产出」的信号流。
# 走线刻意用 45° 折线而非贝塞尔曲线，贴合电路板布线的观感。
WIRES = [
    ("M804,150 H862 L910,102 H946", "0s", "cyan"),
    ("M804,150 H862 L910,198 H946", "0.55s", "cyan"),
    ("M946,102 H1010 L1048,64 H1096", "1.0s", "indigo"),
    ("M946,102 H1028 L1048,122 H1096", "1.45s", "mint"),
    ("M946,198 H1028 L1048,178 H1096", "1.25s", "indigo"),
    ("M946,198 H1010 L1048,236 H1096", "1.7s", "mint"),
]
NODES = [
    (804, 150, 7.5, "cyan", "0s"),
    (946, 102, 5.5, "cyan", "0.4s"),
    (946, 198, 5.5, "cyan", "0.8s"),
    (1096, 64, 4.5, "indigo", "1.2s"),
    (1096, 122, 4.5, "mint", "1.6s"),
    (1096, 178, 4.5, "indigo", "2.0s"),
    (1096, 236, 4.5, "mint", "2.4s"),
]
PILLARS = ["AI 自动化", "嵌入式硬件", "全栈工具链", "游戏原型"]


def hero(t: dict[str, str]) -> str:
    wires = "\n".join(
        f'    <path d="{d}" class="wire"/>\n'
        f'    <path d="{d}" class="pulse" stroke="{t[c]}" style="animation-delay:{delay}"/>'
        for d, delay, c in WIRES
    )
    nodes = "\n".join(
        f'    <circle cx="{x}" cy="{y}" r="{r * 2.2:.1f}" fill="{t[c]}" class="halo"'
        f' style="animation-delay:{delay}"/>\n'
        f'    <circle cx="{x}" cy="{y}" r="{r}" fill="{t[c]}"/>\n'
        f'    <circle cx="{x}" cy="{y}" r="{r * 0.42:.1f}" fill="{t["bg0"]}"/>'
        for x, y, r, c, delay in NODES
    )
    px = 58.0
    pillars_parts = []
    for label in PILLARS:
        pillars_parts.append(
            f'    <circle cx="{px + 2.5:.0f}" cy="204" r="2.5" fill="{t["cyan"]}" opacity=".85"/>'
            f'<text x="{px + 13:.0f}" y="208" class="mono dim">{esc(label)}</text>'
        )
        px += 13 + text_width(label, 12.5) + 30
    pillars = "\n".join(pillars_parts)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="300" viewBox="0 0 1200 300" role="img" aria-label="sharp_caterpillar：把想法做成能跑的系统">
  <title>sharp_caterpillar — 把想法做成能跑的系统</title>
  <defs>
    <linearGradient id="plate" x1="0" y1="0" x2="1200" y2="300" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{t['bg1']}"/>
      <stop offset=".55" stop-color="{t['bg0']}"/>
      <stop offset="1" stop-color="{t['bg1']}"/>
    </linearGradient>
    <linearGradient id="ink" x1="56" y1="96" x2="496" y2="140" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{t['cyan']}"/>
      <stop offset=".52" stop-color="{t['indigo']}"/>
      <stop offset="1" stop-color="{t['mint']}"/>
    </linearGradient>
    <linearGradient id="scan" x1="0" y1="0" x2="1200" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{t['cyan']}" stop-opacity="0"/>
      <stop offset=".28" stop-color="{t['cyan']}"/>
      <stop offset=".62" stop-color="{t['indigo']}"/>
      <stop offset="1" stop-color="{t['mint']}" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="glowA">
      <stop offset="0" stop-color="{t['cyan']}" stop-opacity="{t['glow']}"/>
      <stop offset="1" stop-color="{t['cyan']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowB">
      <stop offset="0" stop-color="{t['indigo']}" stop-opacity="{t['glow']}"/>
      <stop offset="1" stop-color="{t['indigo']}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="26" height="26" patternUnits="userSpaceOnUse">
      <path d="M26 0H0V26" fill="none" stroke="{t['grid']}" stroke-width="1"/>
    </pattern>
    <clipPath id="plate-clip"><rect width="1200" height="300" rx="22"/></clipPath>
  </defs>
  <style>
    .name {{ font: 800 46px {FONT}; fill: url(#ink); letter-spacing: -1.2px; }}
    .lead {{ font: 600 25px {FONT}; fill: {t['text']}; }}
    .mono {{ font: 500 12.5px {MONO}; }}
    .tag  {{ font: 600 12px {MONO}; fill: {t['cyan']}; letter-spacing: .5px; }}
    .dim {{ fill: {t['dim']}; }}
    .faint {{ fill: {t['faint']}; }}
    .wire {{ fill: none; stroke: {t['wire']}; stroke-width: 1.8; stroke-linejoin: round;
             stroke-linecap: round; }}
    .pulse {{ fill: none; stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round;
              stroke-dasharray: 18 150; animation: flow 3.2s linear infinite; }}
    .halo {{ animation: breathe 3.4s ease-in-out infinite; }}
    @keyframes flow {{ from {{ stroke-dashoffset: 168 }} to {{ stroke-dashoffset: 0 }} }}
    @keyframes breathe {{ 0%, 100% {{ opacity: .08 }} 50% {{ opacity: .26 }} }}
  </style>
  <g clip-path="url(#plate-clip)">
    <rect width="1200" height="300" fill="url(#plate)"/>
    <rect width="1200" height="300" fill="url(#grid)" opacity="{t['gridop']}"/>
    <ellipse cx="120" cy="8" rx="440" ry="240" fill="url(#glowA)"/>
    <ellipse cx="1020" cy="150" rx="400" ry="250" fill="url(#glowB)"/>

    <rect x="56" y="40" width="228" height="27" rx="13.5" fill="{t['surface']}" stroke="{t['line']}"/>
    <circle cx="73" cy="53.5" r="3.6" fill="{t['mint']}">
      <animate attributeName="opacity" values="1;.28;1" dur="2.4s" repeatCount="indefinite"/>
    </circle>
    <text x="88" y="58" class="tag">STUDENT DEVELOPER · UTC+8</text>

    <text x="56" y="130" class="name">sharp_caterpillar</text>
    <text x="56" y="172" class="lead">把想法做成能跑的系统</text>
{pillars}
    <text x="56" y="243" class="mono faint">ESP32-S3 · OpenCV · Spring Boot · Vue 3 · Electron · Godot 4</text>

    <g>
{wires}
{nodes}
    </g>
    <text x="950" y="278" class="mono faint" text-anchor="middle">idea  ──▶  prototype  ──▶  shipped system</text>

    <rect y="297" width="1200" height="3" fill="url(#scan)"/>
  </g>
</svg>
"""


# ---------------------------------------------------------------- 技术栈

# 每一项都能在公开仓库里找到对应实现，不写没做过的东西
STACK: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("EMBEDDED", "cyan", [
        ("ESP32-S3", "#e7352c"), ("STM32", "#03234b"), ("51 MCU", "#7c8794"),
        ("传感器 / I²C", "#0ea5e9"), ("华为云 IoT", "#cf0a2c"),
    ]),
    ("AI & AUTOMATION", "indigo", [
        ("OpenCV", "#5c3ee8"), ("Playwright", "#2ead33"), ("通义千问", "#615ced"),
        ("DeepSeek", "#4d6bfe"), ("Python", "#3776ab"),
    ]),
    ("BACKEND", "mint", [
        ("Spring Boot", "#6db33f"), ("Flask", "#4a5568"), ("Java", "#e76f00"),
        ("PostgreSQL", "#4169e1"), ("MySQL", "#00758f"),
    ]),
    ("FRONTEND & DESKTOP", "amber", [
        ("Vue 3", "#41b883"), ("TypeScript", "#3178c6"), ("Three.js", "#049ef4"),
        ("Electron", "#47848f"), ("Qt / C++", "#41cd52"), ("微信小程序", "#07c160"),
    ]),
    ("GAME & LOW-LEVEL", "cyan", [
        ("Godot 4", "#478cbf"), ("GDScript", "#5286a8"), ("C", "#8899aa"), ("Git", "#f05033"),
    ]),
]


def readable(color: str, theme: str) -> str:
    """把品牌色压进当前主题的可读亮度区间，避免深蓝在暗底上消失。"""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    if theme == "dark" and lum < 0.50:
        scale = 0.50 / max(lum, 0.05)
    elif theme == "light" and lum > 0.70:
        scale = 0.70 / lum
    else:
        return color
    r, g, b = (max(0, min(255, round(c * scale))) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def text_width(label: str, size: float = 13.0) -> float:
    """粗略估算文本像素宽度：CJK 按全宽算，ASCII 按 0.56em 算。"""
    return sum(size if ord(ch) > 0x2E80 else size * 0.56 for ch in label)


def plate_defs(t: dict[str, str], w: int, h: int) -> str:
    """卡片类资产共用的底板定义：斜向渐变、网格、顶部高光线。"""
    return f"""    <linearGradient id="plate" x1="0" y1="0" x2="{w}" y2="{h}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{t['bg1']}"/>
      <stop offset=".6" stop-color="{t['bg0']}"/>
      <stop offset="1" stop-color="{t['bg1']}"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="{w}" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{t['cyan']}" stop-opacity="0"/>
      <stop offset=".3" stop-color="{t['cyan']}" stop-opacity=".85"/>
      <stop offset=".7" stop-color="{t['indigo']}" stop-opacity=".85"/>
      <stop offset="1" stop-color="{t['mint']}" stop-opacity="0"/>
    </linearGradient>
    <pattern id="grid" width="26" height="26" patternUnits="userSpaceOnUse">
      <path d="M26 0H0V26" fill="none" stroke="{t['grid']}" stroke-width="1"/>
    </pattern>
    <clipPath id="plate-clip"><rect width="{w}" height="{h}" rx="20"/></clipPath>"""


def plate_body(t: dict[str, str], w: int, h: int) -> str:
    return f"""  <g clip-path="url(#plate-clip)">
    <rect width="{w}" height="{h}" fill="url(#plate)"/>
    <rect width="{w}" height="{h}" fill="url(#grid)" opacity="{t['gridop']}"/>
    <rect width="{w}" height="2" fill="url(#edge)"/>
  </g>
  <rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="19.5" fill="none" stroke="{t['line']}" stroke-width="1.5"/>"""


def flow_row(items: list[tuple[str, str]], x0: float, limit: float, gap: float = 8):
    """把 chip 依次排布，超出右边界自动换行。"""
    rows: list[list[tuple[float, float, str, str]]] = []
    row: list[tuple[float, float, str, str]] = []
    x = x0
    for label, brand in items:
        w = text_width(label) + 38
        if row and x + w > limit:
            rows.append(row)
            row, x = [], x0
        row.append((x, w, label, brand))
        x += w + gap
    if row:
        rows.append(row)
    return rows


def stack(t: dict[str, str], theme: str) -> str:
    W, X0, LIMIT, ROW, GAP_BLOCK, PAD = 1200, 224, 1156, 34, 20, 26
    y = PAD
    blocks: list[str] = []

    for index, (name, ckey, items) in enumerate(STACK):
        rows = flow_row(items, X0, LIMIT)
        parts = [
            f'    <rect x="44" y="{y + 5}" width="3" height="16" rx="1.5" fill="{t[ckey]}"/>',
            f'    <text x="58" y="{y + 17.4}" class="group">{esc(name)}</text>',
        ]
        for ri, row in enumerate(rows):
            ry = y + ri * ROW
            for cx, cw, label, brand in row:
                parts.append(
                    f'    <g transform="translate({cx:.0f} {ry})">'
                    f'<rect width="{cw:.0f}" height="26" rx="8" fill="{t["surface"]}"'
                    f' stroke="{t["line"]}"/>'
                    f'<circle cx="13" cy="13" r="3.6" fill="{readable(brand, theme)}"/>'
                    f'<text x="25" y="17.6" class="chip">{esc(label)}</text></g>'
                )
        blocks.append("\n".join(parts))
        y += len(rows) * ROW - (ROW - 26)
        if index < len(STACK) - 1:
            y += GAP_BLOCK

    H = y + PAD
    body = "\n".join(blocks)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="技术栈分组">
  <title>Toolbox — 分组技术栈</title>
  <defs>
{plate_defs(t, W, H)}
  </defs>
  <style>
    .group {{ font: 700 11px {MONO}; fill: {t['dim']}; letter-spacing: 1.2px; }}
    .chip {{ font: 500 13px {FONT}; fill: {t['text']}; }}
  </style>
{plate_body(t, W, H)}
{body}
</svg>
"""


# ---------------------------------------------------------------- GitHub 数据

LANG_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Python": "#3572a5",
    "C": "#555555", "C++": "#f34b7d", "Java": "#b07219", "HTML": "#e34c26",
    "CSS": "#563d7c", "GDScript": "#355570", "Vue": "#41b883", "Shell": "#89e051",
    "Other": "#8b949e",
}
PLACEHOLDER = {
    "repos": 0, "stars": 0, "forks": 0, "followers": 0, "since": "2019",
    "langs": [], "updated": "—",
}


def api(path: str) -> object:
    """GET GitHub REST API。代理走标准 HTTPS_PROXY 环境变量。"""
    request = urllib.request.Request(f"{API_ROOT}{path}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_stats(offline: bool) -> dict:
    if not offline:
        try:
            user = api(f"/users/{USERNAME}")
            repos: list[dict] = []
            page = 1
            while True:
                batch = api(f"/users/{USERNAME}/repos?type=owner&per_page=100&page={page}")
                if not batch:
                    break
                repos.extend(r for r in batch if not r.get("fork"))
                page += 1

            volume: Counter[str] = Counter()
            for repo in repos:
                if repo.get("language"):
                    volume[str(repo["language"])] += int(repo.get("size", 0)) or 1
            total = sum(volume.values()) or 1
            top = volume.most_common(6)
            langs = [(name, size / total * 100) for name, size in top]
            rest = 100 - sum(pct for _, pct in langs)
            if rest > 0.8:
                langs.append(("Other", rest))

            data = {
                "repos": len(repos),
                "stars": sum(int(r.get("stargazers_count", 0)) for r in repos),
                "forks": sum(int(r.get("forks_count", 0)) for r in repos),
                "followers": int(user.get("followers", 0)),
                "since": str(user.get("created_at", "2019"))[:4],
                "langs": langs,
                "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return data
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print(f"  ! GitHub API 不可用（{exc}），回退到缓存")

    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return dict(PLACEHOLDER)


def stats(t: dict[str, str], theme: str, data: dict) -> str:
    W, H, PAD, BAR_W = 1200, 272, 44, 1112
    cards = [
        ("stars earned", data["stars"], "amber"),
        ("public repos", data["repos"], "cyan"),
        ("forks", data["forks"], "indigo"),
        ("followers", data["followers"], "mint"),
    ]
    card_w = (BAR_W - 3 * 16) / 4
    tiles = "\n".join(
        f'    <g transform="translate({PAD + i * (card_w + 16):.0f} 64)">'
        f'<rect width="{card_w:.0f}" height="86" rx="14" fill="{t["surface"]}"'
        f' stroke="{t["line"]}"/>'
        f'<rect x="{card_w / 2 - 19:.0f}" y="18" width="38" height="3" rx="1.5"'
        f' fill="{t[accent]}"/>'
        f'<text x="{card_w / 2:.0f}" y="54" class="big" text-anchor="middle">{value}</text>'
        f'<text x="{card_w / 2:.0f}" y="73" class="cap" text-anchor="middle">{esc(label)}</text>'
        f"</g>"
        for i, (label, value, accent) in enumerate(cards)
    )

    langs = data["langs"] or [("no data", 100.0)]
    segments, legend, x, lx = [], [], float(PAD), float(PAD)
    for name, pct in langs:
        # "Other" 用主题灰，和被提亮的 C / 51 MCU 等中性色区分开
        color = (
            t["faint"] if name == "Other"
            else readable(LANG_COLORS.get(name, LANG_COLORS["Other"]), theme)
        )
        width = BAR_W * pct / 100
        segments.append(
            f'      <rect x="{x:.1f}" y="204" width="{width:.1f}" height="14" fill="{color}"/>'
        )
        x += width
        label = f"{name} {pct:.1f}%"
        legend.append(
            f'    <circle cx="{lx + 4:.0f}" cy="242" r="4" fill="{color}"/>'
            f'<text x="{lx + 15:.0f}" y="246.5" class="legend">{esc(label)}</text>'
        )
        lx += 15 + text_width(label, 12) + 26

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub 数据概览">
  <title>Signals — GitHub 数据概览</title>
  <defs>
{plate_defs(t, W, H)}
    <clipPath id="bar-clip"><rect x="{PAD}" y="204" width="{BAR_W}" height="14" rx="7"/></clipPath>
  </defs>
  <style>
    .h {{ font: 700 13px {MONO}; fill: {t['dim']}; letter-spacing: 2.2px; }}
    .meta {{ font: 500 11.5px {MONO}; fill: {t['faint']}; }}
    .big {{ font: 800 34px {FONT}; fill: {t['text']}; }}
    .cap {{ font: 600 10.5px {MONO}; fill: {t['dim']}; letter-spacing: 1.1px; }}
    .legend {{ font: 500 12px {MONO}; fill: {t['dim']}; }}
  </style>
{plate_body(t, W, H)}
    <text x="{PAD}" y="42" class="h">SIGNALS</text>
    <text x="{PAD + BAR_W}" y="42" class="meta" text-anchor="end">since {esc(data['since'])} · updated {esc(data['updated'])}</text>
{tiles}
    <text x="{PAD}" y="192" class="h">LANGUAGE MIX</text>
    <rect x="{PAD}" y="204" width="{BAR_W}" height="14" rx="7" fill="{t['grid']}"/>
    <g clip-path="url(#bar-clip)">
{chr(10).join(segments)}
    </g>
{chr(10).join(legend)}
</svg>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="构建个人主页 SVG 资产")
    parser.add_argument(
        "--offline", action="store_true", help="跳过 GitHub API，用上次缓存的数据渲染"
    )
    args = parser.parse_args()

    data = fetch_stats(args.offline)
    print(
        f"数据：{data['repos']} repos · {data['stars']} stars · "
        f"{data['forks']} forks · {data['followers']} followers"
    )
    for name, tokens in THEMES.items():
        write(f"hero-{name}.svg", hero(tokens))
        write(f"stack-{name}.svg", stack(tokens, name))
        write(f"stats-{name}.svg", stats(tokens, name, data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
