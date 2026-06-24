import html


def bar_svg(counter, title, width=900, height=260):
    if not counter:
        return f"<h3>{html.escape(title)}</h3><p>无数据</p>"

    items = list(counter.items())
    max_v = max(v for _, v in items) if items else 1
    max_v = max(max_v, 1)

    margin_left = 50
    margin_bottom = 50
    margin_top = 30
    chart_width = width - margin_left - 30
    chart_height = height - margin_top - margin_bottom

    bar_gap = 6
    bar_width = max(8, (chart_width - bar_gap * len(items)) / max(len(items), 1))

    parts = [
        f"<h3>{html.escape(title)}</h3>",
        f'<svg width="{width}" height="{height}" style="background:#fff;border:1px solid #eee;">',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + chart_height}" stroke="#333"/>',
        f'<line x1="{margin_left}" y1="{margin_top + chart_height}" x2="{width - 20}" y2="{margin_top + chart_height}" stroke="#333"/>',
    ]

    for idx, (k, v) in enumerate(items):
        x = margin_left + idx * (bar_width + bar_gap) + bar_gap
        h = chart_height * v / max_v
        y = margin_top + chart_height - h

        label = str(k)
        if len(label) > 10:
            label = label[:10] + "..."

        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{h:.1f}" fill="#4e79a7"/>'
        )
        parts.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{y - 4:.1f}" font-size="10" text-anchor="middle">{v}</text>'
        )
        parts.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{margin_top + chart_height + 16}" font-size="10" text-anchor="middle">{html.escape(label)}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)