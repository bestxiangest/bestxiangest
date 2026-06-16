#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


USERNAME = os.environ.get("PROFILE_USERNAME", "bestxiangest")
OUTPUT = Path("assets/profile-summary.svg")
API_ROOT = "https://api.github.com"


def token() -> str:
    value = os.environ.get("GITHUB_TOKEN", "").strip()
    if value:
        return value
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        return ""


TOKEN = token()


def request_json(path: str):
    try:
        env = os.environ.copy()
        if TOKEN:
            env["GH_TOKEN"] = TOKEN
        return json.loads(
            subprocess.check_output(["gh", "api", path], text=True, env=env)
        )
    except Exception:
        pass

    req = urllib.request.Request(f"{API_ROOT}{path}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API failed: {exc.code} {message}") from exc


def all_public_repos() -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        batch = request_json(
            f"/users/{USERNAME}/repos?type=owner&sort=updated&per_page=100&page={page}"
        )
        if not batch:
            return repos
        repos.extend(repo for repo in batch if not repo.get("private"))
        page += 1


def top_languages(repos: list[dict]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for repo in repos:
        language = repo.get("language")
        if language:
            counts[str(language)] += 1
    return counts.most_common(6)


def svg_bar(x: int, y: int, width: int, color: str, label: str, pct: float) -> str:
    filled = max(8, round(width * pct))
    return f"""
    <text x="{x}" y="{y}" class="small">{html.escape(label)}</text>
    <text x="{x + width - 44}" y="{y}" class="small muted">{pct * 100:.0f}%</text>
    <rect x="{x}" y="{y + 10}" width="{width}" height="9" rx="4.5" fill="#e2e8f0"/>
    <rect x="{x}" y="{y + 10}" width="{filled}" height="9" rx="4.5" fill="{color}"/>"""


def stat_card(x: int, label: str, value: str, color: str) -> str:
    return f"""
    <g transform="translate({x} 68)">
      <rect width="196" height="92" rx="20" fill="#ffffff" stroke="#dbeafe"/>
      <circle cx="38" cy="35" r="15" fill="{color}" opacity="0.18"/>
      <circle cx="38" cy="35" r="6" fill="{color}"/>
      <text x="68" y="39" class="value">{html.escape(value)}</text>
      <text x="24" y="68" class="small muted">{html.escape(label)}</text>
    </g>"""


def generate() -> str:
    user = request_json(f"/users/{USERNAME}")
    repos = all_public_repos()
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in repos)
    forks = sum(int(repo.get("forks_count", 0)) for repo in repos)
    langs = top_languages(repos)
    lang_total = sum(count for _, count in langs) or 1
    updated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    colors = ["#0ea5e9", "#14b8a6", "#f59e0b", "#a855f7", "#ef4444", "#64748b"]

    bars = []
    for index, (name, count) in enumerate(langs):
        x = 42 if index < 3 else 500
        y = 220 + (index % 3) * 34
        bars.append(svg_bar(x, y, 360, colors[index % len(colors)], name, count / lang_total))

    return f"""<svg width="960" height="340" viewBox="0 0 960 340" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">bestxiangest profile summary</title>
  <desc id="desc">Local GitHub profile summary generated from GitHub API.</desc>
  <style>
    .title {{ font: 800 26px Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #0f172a; }}
    .value {{ font: 800 27px Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #0f172a; }}
    .small {{ font: 600 14px Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #334155; }}
    .muted {{ fill: #64748b; }}
    .mono {{ font: 600 13px SFMono-Regular, Consolas, "Liberation Mono", monospace; fill: #64748b; }}
  </style>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="960" y2="300" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="0.52" stop-color="#f8fafc"/>
      <stop offset="1" stop-color="#ecfeff"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="958" height="338" rx="28" fill="url(#bg)" stroke="#dbeafe"/>
  <text x="42" y="42" class="title">Local profile signals</text>
  <text x="690" y="42" class="mono">updated {html.escape(updated)}</text>
  {stat_card(42, "Public repositories", str(len(repos)), "#0ea5e9")}
  {stat_card(260, "Stars earned", str(stars), "#f59e0b")}
  {stat_card(478, "Followers", str(user.get("followers", 0)), "#14b8a6")}
  {stat_card(696, "Forks across repos", str(forks), "#a855f7")}
  <text x="42" y="194" class="title">Language mix</text>
  <text x="500" y="194" class="mono">Generated in this repository to avoid public badge API limits.</text>
  {"".join(bars)}
</svg>
"""


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generate(), encoding="utf-8")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
