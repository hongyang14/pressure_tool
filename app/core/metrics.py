import statistics
from collections import Counter


def percentile(values, p):
    if not values:
        return 0.0

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    k = (len(values) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(values) - 1)

    if f == c:
        return values[f]

    return values[f] * (c - k) + values[c] * (k - f)


def calculate_metrics(results, wall_time):
    total = len(results)
    success_count = sum(1 for r in results if r.success)
    fail_count = total - success_count

    latencies = [r.latency_ms for r in results]
    success_latencies = [r.latency_ms for r in results if r.success]
    first_frame_latencies = [
        r.first_frame_latency_ms
        for r in results
        if r.first_frame_latency_ms and r.first_frame_latency_ms > 0
    ]
    success_first_frame_latencies = [
        r.first_frame_latency_ms
        for r in results
        if r.success and r.first_frame_latency_ms and r.first_frame_latency_ms > 0
    ]

    status_counter = Counter(
        str(r.status_code) if r.status_code is not None else "EXCEPTION"
        for r in results
    )

    error_counter = Counter(
        r.error if r.error else "无错误"
        for r in results
        if not r.success
    )

    rps_counter = Counter(r.relative_end_second for r in results)

    total_bytes = sum(r.response_bytes for r in results)

    qps = total / wall_time if wall_time > 0 else 0
    success_qps = success_count / wall_time if wall_time > 0 else 0

    # TPS 定义为每秒成功事务数
    tps = success_count / wall_time if wall_time > 0 else 0

    return {
        "total": total,
        "success_count": success_count,
        "fail_count": fail_count,
        "success_rate": success_count / total * 100 if total else 0,
        "fail_rate": fail_count / total * 100 if total else 0,
        "wall_time": wall_time,

        "qps": qps,
        "success_qps": success_qps,
        "tps": tps,

        "avg_latency": statistics.mean(latencies) if latencies else 0,
        "success_avg_latency": statistics.mean(success_latencies) if success_latencies else 0,
        "min_latency": min(latencies) if latencies else 0,
        "max_latency": max(latencies) if latencies else 0,

        "p50_latency": percentile(latencies, 50),
        "p90_latency": percentile(latencies, 90),
        "p95_latency": percentile(latencies, 95),
        "p99_latency": percentile(latencies, 99),

        "avg_first_frame_latency": statistics.mean(first_frame_latencies) if first_frame_latencies else 0,
        "success_avg_first_frame_latency": statistics.mean(success_first_frame_latencies) if success_first_frame_latencies else 0,
        "min_first_frame_latency": min(first_frame_latencies) if first_frame_latencies else 0,
        "max_first_frame_latency": max(first_frame_latencies) if first_frame_latencies else 0,
        "p50_first_frame_latency": percentile(first_frame_latencies, 50),
        "p90_first_frame_latency": percentile(first_frame_latencies, 90),
        "p95_first_frame_latency": percentile(first_frame_latencies, 95),
        "p99_first_frame_latency": percentile(first_frame_latencies, 99),

        "avg_response_bytes": total_bytes / total if total else 0,
        "status_counter": dict(status_counter),
        "error_counter": dict(error_counter),
        "rps_counter": dict(sorted(rps_counter.items())),
        "body_template_metrics": calculate_body_template_metrics(results),
    }


def calculate_body_template_metrics(results):
    grouped = {}
    for result in results:
        if result.body_template_index is None:
            continue
        grouped.setdefault(result.body_template_index, []).append(result)

    metrics = []
    for index in sorted(grouped):
        items = grouped[index]
        total = len(items)
        success_count = sum(1 for r in items if r.success)
        fail_count = total - success_count
        latencies = [r.latency_ms for r in items]
        first_frame_latencies = [
            r.first_frame_latency_ms
            for r in items
            if r.first_frame_latency_ms and r.first_frame_latency_ms > 0
        ]
        status_counter = Counter(
            str(r.status_code) if r.status_code is not None else "EXCEPTION"
            for r in items
        )
        error_counter = Counter(
            r.error if r.error else "无错误"
            for r in items
            if not r.success
        )

        metrics.append({
            "body_template_index": index,
            "body_template_label": f"Body #{index}",
            "total": total,
            "success_count": success_count,
            "fail_count": fail_count,
            "success_rate": success_count / total * 100 if total else 0,
            "avg_latency": statistics.mean(latencies) if latencies else 0,
            "p95_latency": percentile(latencies, 95),
            "avg_first_frame_latency": statistics.mean(first_frame_latencies) if first_frame_latencies else 0,
            "p95_first_frame_latency": percentile(first_frame_latencies, 95),
            "status_counter": dict(status_counter),
            "error_counter": dict(error_counter),
        })

    return metrics
