from __future__ import annotations

from html import escape
import json

from .contracts import AcceptanceCheck, AcceptanceReport, CheckStatus


def _json_html(value: object) -> str:
    return escape(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True),
        quote=False,
    )


def _check_card(value: AcceptanceCheck) -> str:
    labels = {
        CheckStatus.PASS: ("PASS", "通过"),
        CheckStatus.FAIL: ("FAIL", "失败"),
        CheckStatus.SKIPPED: ("SKIP", "未执行"),
    }
    badge, label = labels[value.status]
    error = ""
    if value.status is CheckStatus.FAIL:
        error = f"""
        <div class="error-box">
          <strong>{escape(value.error_type or 'Error')}</strong>
          <span>{escape(value.error_message or '验收失败')}</span>
        </div>
        """
    return f"""
    <article class="check-card {value.status.value}">
      <div class="check-head">
        <span class="status-badge">{badge}</span>
        <span class="duration">{value.duration_ms} ms</span>
      </div>
      <h3>{escape(value.title)}</h3>
      <p>{escape(value.summary)}</p>
      {error}
      <details>
        <summary>查看验收证据</summary>
        <pre>{_json_html(value.evidence)}</pre>
      </details>
    </article>
    """


def render_report_html(report: AcceptanceReport) -> str:
    if report.status == "pass":
        hero_title = "全部通过"
        hero_text = "ME-System 一键体验验收成功"
        hero_class = "pass"
    elif report.status == "fail":
        hero_title = "验收未通过"
        hero_text = "请展开失败卡片查看可操作信息"
        hero_class = "fail"
    else:
        hero_title = "部分完成"
        hero_text = "存在尚未执行的验收项"
        hero_class = "partial"

    cards = "".join(_check_card(value) for value in report.checks)
    highlights = "".join(
        f"<div class=\"highlight\"><span>{escape(str(key))}</span>"
        f"<strong>{escape(str(value))}</strong></div>"
        for key, value in report.highlights.items()
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ME-System · 小白一键体验验收</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #07100d;
      --panel: rgba(19, 33, 28, .86);
      --panel-strong: #14241e;
      --line: rgba(195, 255, 225, .14);
      --text: #f1f7f4;
      --muted: #9ab0a7;
      --accent: #7df7b8;
      --accent-2: #c4ff77;
      --danger: #ff8f8f;
      --warning: #ffd479;
      --shadow: 0 28px 80px rgba(0, 0, 0, .34);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      background:
        radial-gradient(circle at 10% 0%, rgba(55, 210, 138, .16), transparent 30rem),
        radial-gradient(circle at 90% 15%, rgba(192, 255, 100, .10), transparent 28rem),
        var(--bg);
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .22;
      background-image: linear-gradient(var(--line) 1px, transparent 1px),
                        linear-gradient(90deg, var(--line) 1px, transparent 1px);
      background-size: 48px 48px;
      mask-image: linear-gradient(to bottom, black, transparent 70%);
    }}
    .shell {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 72px; }}
    nav {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }}
    .brand {{ display: flex; gap: 12px; align-items: center; font-weight: 760; letter-spacing: -.02em; }}
    .mark {{
      width: 36px; height: 36px; display: grid; place-items: center; border-radius: 12px;
      background: linear-gradient(145deg, var(--accent), var(--accent-2)); color: #07100d;
      box-shadow: 0 10px 30px rgba(125, 247, 184, .22);
    }}
    .run-meta {{ color: var(--muted); font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .hero {{
      position: relative; overflow: hidden; padding: clamp(28px, 6vw, 62px);
      border: 1px solid var(--line); border-radius: 32px; background: var(--panel); box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }}
    .hero::after {{
      content: ""; position: absolute; width: 320px; height: 320px; right: -90px; top: -130px;
      border-radius: 50%; background: var(--accent); filter: blur(85px); opacity: .10;
    }}
    .eyebrow {{ color: var(--accent); font-weight: 700; letter-spacing: .14em; font-size: 12px; text-transform: uppercase; }}
    h1 {{ margin: 12px 0 8px; font-size: clamp(40px, 8vw, 82px); line-height: .98; letter-spacing: -.065em; }}
    .hero.fail h1 {{ color: var(--danger); }}
    .hero.partial h1 {{ color: var(--warning); }}
    .hero-copy {{ color: var(--muted); font-size: clamp(16px, 2.5vw, 22px); margin: 0 0 28px; }}
    .metrics {{ display: flex; flex-wrap: wrap; gap: 12px; }}
    .metric {{ min-width: 128px; padding: 14px 16px; background: rgba(0,0,0,.18); border: 1px solid var(--line); border-radius: 16px; }}
    .metric strong {{ display: block; font-size: 24px; }}
    .metric span {{ color: var(--muted); font-size: 12px; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 28px; }}
    button, .button {{
      border: 0; border-radius: 14px; padding: 12px 17px; cursor: pointer; text-decoration: none;
      font: inherit; font-weight: 720; background: linear-gradient(135deg, var(--accent), var(--accent-2)); color: #07100d;
    }}
    .button.secondary {{ background: transparent; color: var(--text); border: 1px solid var(--line); }}
    button[disabled] {{ opacity: .55; cursor: wait; }}
    .section-head {{ display: flex; align-items: end; justify-content: space-between; gap: 20px; margin: 48px 0 18px; }}
    .section-head h2 {{ margin: 0; font-size: 26px; letter-spacing: -.035em; }}
    .section-head p {{ margin: 0; color: var(--muted); }}
    .check-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .check-card {{
      min-width: 0; padding: 22px; background: var(--panel); border: 1px solid var(--line); border-radius: 22px;
      box-shadow: 0 14px 36px rgba(0,0,0,.18);
    }}
    .check-card.pass {{ border-color: rgba(125,247,184,.24); }}
    .check-card.fail {{ border-color: rgba(255,143,143,.42); }}
    .check-card.skipped {{ border-color: rgba(255,212,121,.30); }}
    .check-head {{ display: flex; justify-content: space-between; align-items: center; }}
    .status-badge {{ font: 700 11px ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--accent); }}
    .fail .status-badge {{ color: var(--danger); }}
    .skipped .status-badge {{ color: var(--warning); }}
    .duration {{ color: var(--muted); font-size: 12px; }}
    .check-card h3 {{ margin: 18px 0 8px; font-size: 19px; }}
    .check-card p {{ color: var(--muted); margin: 0; line-height: 1.65; }}
    details {{ margin-top: 18px; border-top: 1px solid var(--line); padding-top: 14px; }}
    summary {{ cursor: pointer; color: #cce0d7; }}
    pre {{ overflow: auto; padding: 14px; border-radius: 14px; background: rgba(0,0,0,.26); color: #bdd9cc; font-size: 12px; line-height: 1.55; }}
    .error-box {{ display: grid; gap: 4px; margin-top: 14px; padding: 12px 14px; border-radius: 12px; background: rgba(255,80,80,.10); color: #ffd0d0; }}
    .highlight-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 14px; }}
    .highlight {{ padding: 20px; border-radius: 20px; background: var(--panel-strong); border: 1px solid var(--line); }}
    .highlight span {{ display: block; color: var(--muted); font-size: 12px; margin-bottom: 10px; }}
    .highlight strong {{ font-size: 18px; overflow-wrap: anywhere; }}
    .technical {{ padding: 24px; border-radius: 22px; background: var(--panel); border: 1px solid var(--line); }}
    footer {{ margin-top: 40px; color: var(--muted); font-size: 12px; text-align: center; }}
    @media (max-width: 760px) {{
      .check-grid, .highlight-grid {{ grid-template-columns: 1fr; }}
      nav {{ align-items: flex-start; gap: 18px; }}
      .run-meta {{ text-align: right; max-width: 48%; overflow-wrap: anywhere; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <nav>
      <div class="brand"><span class="mark">M</span><span>ME-System</span></div>
      <div class="run-meta">{escape(report.run_id)} · v{escape(report.version)}</div>
    </nav>

    <section class="hero {hero_class}">
      <div class="eyebrow">NOVICE ONE-CLICK ACCEPTANCE</div>
      <h1>{hero_title}</h1>
      <p class="hero-copy">{hero_text}</p>
      <div class="metrics">
        <div class="metric"><strong>{report.passed_count}/{len(report.checks)}</strong><span>通过项目</span></div>
        <div class="metric"><strong>{report.duration_ms} ms</strong><span>总验收耗时</span></div>
        <div class="metric"><strong>{report.failed_count}</strong><span>失败项目</span></div>
      </div>
      <div class="actions">
        <button id="rerun" type="button">重新验收</button>
        <a class="button secondary" href="/api/report" download="me-system-acceptance.json">下载 JSON 报告</a>
      </div>
    </section>

    <div class="section-head"><div><h2>逐项验收</h2><p>不是演示动画，而是真实数据库、审核和 MCP 调用。</p></div></div>
    <section class="check-grid">{cards}</section>

    <div class="section-head"><div><h2>你已经验证了什么</h2><p>面向使用者的关键结果。</p></div></div>
    <section class="highlight-grid">{highlights or '<div class="highlight"><span>状态</span><strong>暂无摘要</strong></div>'}</section>

    <div class="section-head"><div><h2>技术证据</h2><p>供开发者和审核者复核。</p></div></div>
    <section class="technical"><pre>{_json_html(report.technical)}</pre></section>

    <footer>本页面只在你的电脑上运行。PostgreSQL 未暴露到宿主机。</footer>
  </main>
  <script>
    const button = document.getElementById('rerun');
    button.addEventListener('click', async () => {{
      button.disabled = true;
      button.textContent = '正在重新验收…';
      try {{
        const response = await fetch('/api/run', {{ method: 'POST' }});
        if (!response.ok) throw new Error('run failed');
        location.reload();
      }} catch (error) {{
        button.disabled = false;
        button.textContent = '重新验收';
        alert('重新验收未能启动，请查看 Docker 日志。');
      }}
    }});
  </script>
</body>
</html>
"""
