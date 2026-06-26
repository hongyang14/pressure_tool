import html
from dataclasses import asdict

from app.report.chart import bar_svg
from app.core.task_model import RUN_MODE_DURATION
from app.utils.time_utils import now_str, format_ms, format_rate


def _run_mode_label(config_dict):
    if config_dict.get("run_mode") == RUN_MODE_DURATION:
        return "按时长"
    return "固定请求数"


def _format_total_requests(config_dict):
    if config_dict.get("run_mode") == RUN_MODE_DURATION:
        return "不限"
    return config_dict["total_requests"]


def _format_duration(config_dict):
    if config_dict.get("run_mode") == RUN_MODE_DURATION:
        return f"{config_dict.get('duration_seconds', 0)} 秒"
    return "不适用"


def _format_think_time(config_dict):
    min_time = config_dict.get("think_time_min", 0)
    max_time = config_dict.get("think_time_max", 0)
    if min_time <= 0 and max_time <= 0:
        return "未启用"
    return f"{min_time} ~ {max_time} 秒"


def _table_rows(counter):
    rows = ""

    for key, value in counter.items():
        rows += f"""
        <tr>
            <td>{html.escape(str(key))}</td>
            <td>{value}</td>
        </tr>
        """

    return rows


def _body_template_rows(body_metrics):
    if not body_metrics:
        return ""

    rows = ""
    for item in body_metrics:
        rows += f"""
        <tr>
            <td>{html.escape(item["body_template_label"])}</td>
            <td>{item["total"]}</td>
            <td class="success">{item["success_count"]}</td>
            <td class="fail">{item["fail_count"]}</td>
            <td>{format_rate(item["success_rate"])}</td>
            <td>{format_ms(item["avg_first_frame_latency"])}</td>
            <td>{format_ms(item["avg_latency"])}</td>
        </tr>
        """
    return rows


def _body_template_section(body_metrics):
    rows = _body_template_rows(body_metrics)
    if not rows:
        return ""

    return f"""
<div class="card">
    <h2>五、Body 数据执行结果</h2>
    <table>
        <tr>
            <th>Body 数据</th>
            <th>请求数</th>
            <th>成功数</th>
            <th>失败数</th>
            <th>成功率</th>
            <th>平均首帧时延</th>
            <th>平均完整耗时</th>
        </tr>
        {rows}
    </table>
</div>
"""


def write_html_report(config, metrics, html_path, csv_filename, json_filename):
    config_dict = asdict(config)

    status_chart = bar_svg(metrics["status_counter"], "状态码分布")
    rps_chart = bar_svg(metrics["rps_counter"], "每秒完成请求数")

    status_rows = _table_rows(metrics["status_counter"])
    error_rows = _table_rows(metrics["error_counter"])
    body_template_section = _body_template_section(metrics.get("body_template_metrics", []))

    if not error_rows:
        error_rows = "<tr><td>无</td><td>0</td></tr>"

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>算法接口压测报告</title>
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
    background: #f6f7f9;
    padding: 24px;
    color: #222;
}}
.container {{
    max-width: 1100px;
    margin: 0 auto;
}}
.card {{
    background: #fff;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 18px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}}
.metric-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}}
.metric {{
    background: #f7f8fa;
    border-radius: 8px;
    padding: 12px;
}}
.metric .name {{
    color: #666;
    font-size: 13px;
}}
.metric .value {{
    font-size: 22px;
    font-weight: bold;
    margin-top: 4px;
}}
.success {{
    color: #1f9d55;
}}
.fail {{
    color: #d93025;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin-top: 10px;
}}
th, td {{
    border: 1px solid #e5e7eb;
    padding: 8px 10px;
    font-size: 14px;
    text-align: left;
}}
th {{
    background: #f0f2f5;
}}
a {{
    color: #2563eb;
}}
</style>
</head>
<body>
<div class="container">

<div class="card">
    <h1>算法接口压测报告</h1>
    <p>生成时间：{html.escape(now_str())}</p>
    <p>
        CSV 明细：
        <a href="./{html.escape(csv_filename)}">{html.escape(csv_filename)}</a>
        &nbsp;&nbsp;
        JSON 原始结果：
        <a href="./{html.escape(json_filename)}">{html.escape(json_filename)}</a>
    </p>
</div>

<div class="card">
    <h2>一、压测配置</h2>
    <table>
        <tr><th>配置项</th><th>值</th></tr>
        <tr><td>URL</td><td>{html.escape(config_dict["url"])}</td></tr>
        <tr><td>Method</td><td>{html.escape(config_dict["method"])}</td></tr>
        <tr><td>并发数</td><td>{config_dict["concurrency"]}</td></tr>
        <tr><td>压测模式</td><td>{html.escape(_run_mode_label(config_dict))}</td></tr>
        <tr><td>总请求数</td><td>{_format_total_requests(config_dict)}</td></tr>
        <tr><td>持续时长</td><td>{_format_duration(config_dict)}</td></tr>
        <tr><td>思考时间</td><td>{_format_think_time(config_dict)}</td></tr>
        <tr><td>Body 数据文件</td><td>{html.escape(config_dict.get("body_data_file") or "未使用")}</td></tr>
        <tr><td>Proto 文件</td><td>{html.escape(config_dict.get("proto_file") or "未使用")}</td></tr>
        <tr><td>首帧超时</td><td>{config_dict.get("first_frame_timeout", config_dict["timeout"])} 秒</td></tr>
        <tr><td>完整超时</td><td>{config_dict["timeout"]} 秒</td></tr>
        <tr><td>Ramp-up</td><td>{config_dict["ramp_up"]} 秒</td></tr>
        <tr><td>成功关键字</td><td>{html.escape(config_dict["success_keyword"])}</td></tr>
    </table>
</div>

<div class="card">
    <h2>二、核心指标</h2>
    <div class="metric-grid">
        <div class="metric"><div class="name">总请求数</div><div class="value">{metrics["total"]}</div></div>
        <div class="metric"><div class="name">成功数</div><div class="value success">{metrics["success_count"]}</div></div>
        <div class="metric"><div class="name">失败数</div><div class="value fail">{metrics["fail_count"]}</div></div>
        <div class="metric"><div class="name">成功率</div><div class="value">{format_rate(metrics["success_rate"])}</div></div>

        <div class="metric"><div class="name">总耗时</div><div class="value">{metrics["wall_time"]:.2f}s</div></div>
        <div class="metric"><div class="name">QPS</div><div class="value">{metrics["qps"]:.2f}</div></div>
        <div class="metric"><div class="name">成功 QPS</div><div class="value">{metrics["success_qps"]:.2f}</div></div>
        <div class="metric"><div class="name">TPS</div><div class="value">{metrics["tps"]:.2f}</div></div>
        <div class="metric"><div class="name">平均响应大小</div><div class="value">{metrics["avg_response_bytes"]:.1f} B</div></div>
    </div>
</div>

<div class="card">
    <h2>三、耗时指标</h2>
    <table>
        <tr><th>指标</th><th>值</th></tr>
        <tr><td>平均首帧时延</td><td>{format_ms(metrics["avg_first_frame_latency"])}</td></tr>
        <tr><td>成功请求平均首帧时延</td><td>{format_ms(metrics["success_avg_first_frame_latency"])}</td></tr>
        <tr><td>最小首帧时延</td><td>{format_ms(metrics["min_first_frame_latency"])}</td></tr>
        <tr><td>最大首帧时延</td><td>{format_ms(metrics["max_first_frame_latency"])}</td></tr>
        <tr><td>首帧 P50</td><td>{format_ms(metrics["p50_first_frame_latency"])}</td></tr>
        <tr><td>首帧 P90</td><td>{format_ms(metrics["p90_first_frame_latency"])}</td></tr>
        <tr><td>首帧 P95</td><td>{format_ms(metrics["p95_first_frame_latency"])}</td></tr>
        <tr><td>首帧 P99</td><td>{format_ms(metrics["p99_first_frame_latency"])}</td></tr>
    </table>
    <h3>完整请求 / 完整流耗时</h3>
    <table>
        <tr><th>指标</th><th>值</th></tr>
        <tr><td>平均完整耗时</td><td>{format_ms(metrics["avg_latency"])}</td></tr>
        <tr><td>成功请求平均完整耗时</td><td>{format_ms(metrics["success_avg_latency"])}</td></tr>
        <tr><td>最小完整耗时</td><td>{format_ms(metrics["min_latency"])}</td></tr>
        <tr><td>最大完整耗时</td><td>{format_ms(metrics["max_latency"])}</td></tr>
        <tr><td>完整耗时 P50</td><td>{format_ms(metrics["p50_latency"])}</td></tr>
        <tr><td>完整耗时 P90</td><td>{format_ms(metrics["p90_latency"])}</td></tr>
        <tr><td>完整耗时 P95</td><td>{format_ms(metrics["p95_latency"])}</td></tr>
        <tr><td>完整耗时 P99</td><td>{format_ms(metrics["p99_latency"])}</td></tr>
    </table>
</div>

<div class="card">
    {rps_chart}
</div>

<div class="card">
    {status_chart}
    <table>
        <tr><th>状态码</th><th>数量</th></tr>
        {status_rows}
    </table>
</div>

<div class="card">
    <h2>四、错误分布</h2>
    <table>
        <tr><th>错误信息</th><th>数量</th></tr>
        {error_rows}
    </table>
</div>

{body_template_section}

<div class="card">
    <h2>六、结论建议</h2>
    <ul>
        <li>如果 P95 / P99 明显高于平均耗时，说明接口存在长尾延迟。</li>
        <li>如果失败率较高，优先查看状态码分布和错误分布。</li>
        <li>如果并发提升后 QPS 不再增长，说明服务端已接近容量瓶颈。</li>
        <li>建议按照不同并发梯度多轮压测，例如 1、5、10、20、50、100。</li>
    </ul>
</div>

</div>
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
