from __future__ import annotations

from datetime import datetime

import anyio
from jinja2 import Template

from llmscope.types.runs import RunRecord

_TEMPLATE: str = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>LLMScope — {{ title }}</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 960px; margin: 48px auto; color: #1a1a1a; }
    h1 { font-size: 1.5rem; margin-bottom: 4px; }
    p.meta { color: #666; font-size: 0.875rem; margin-bottom: 24px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th { text-align: left; padding: 8px 12px; border-bottom: 2px solid #e5e7eb; color: #555; font-weight: 600; }
    td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; }
    tr:hover td { background: #f9fafb; }
  </style>
</head>
<body>
  <h1>LLMScope — {{ title }}</h1>
  <p class="meta">Generated {{ generated_at }} &middot; {{ runs|length }} run(s)</p>
  <table>
    <thead>
      <tr>
        <th>Run ID</th>
        <th>Model</th>
        <th>Backend</th>
        <th>TTFT (ms)</th>
        <th>TPS</th>
        <th>Tokens</th>
        <th>Quality</th>
        <th>Created</th>
      </tr>
    </thead>
    <tbody>
      {% for r in runs %}
      <tr>
        <td>{{ r.run_id[:8] }}</td>
        <td>{{ r.model }}</td>
        <td>{{ r.backend }}</td>
        <td>{{ r.ttft_ms if r.ttft_ms is not none else "—" }}</td>
        <td>{{ r.tps if r.tps is not none else "—" }}</td>
        <td>{{ r.token_count if r.token_count is not none else "—" }}</td>
        <td>{{ r.quality_score if r.quality_score is not none else "—" }}</td>
        <td>{{ r.created_at.strftime("%Y-%m-%d %H:%M") }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>"""


class HtmlReportExporter:
    async def export(
        self,
        runs: list[RunRecord],
        output_path: str,
        title: str = "Run Report",
    ) -> None:
        html: str = Template(_TEMPLATE).render(
            runs=runs,
            title=title,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        async with await anyio.open_file(output_path, "w", encoding="utf-8") as f:
            await f.write(html)
