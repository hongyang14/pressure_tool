from pathlib import Path

from app.report.csv_report import write_csv_report
from app.report.html_report import write_html_report
from app.report.json_report import write_json_report
from app.utils.file_utils import ensure_dir
from app.utils.time_utils import timestamp_str


class ReportGenerator:
    def generate(self, config, results, metrics):
        output_dir = ensure_dir(config.output_dir)

        base_name = f"pressure_report_{timestamp_str()}"

        csv_path = Path(output_dir) / f"{base_name}_detail.csv"
        json_path = Path(output_dir) / f"{base_name}_raw.json"
        html_path = Path(output_dir) / f"{base_name}.html"

        write_csv_report(results, csv_path)
        write_json_report(results, metrics, json_path)
        write_html_report(
            config=config,
            metrics=metrics,
            html_path=html_path,
            csv_filename=csv_path.name,
            json_filename=json_path.name,
        )

        return {
            "html_path": str(html_path),
            "csv_path": str(csv_path),
            "json_path": str(json_path),
        }