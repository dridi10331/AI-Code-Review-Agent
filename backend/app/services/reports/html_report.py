from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.app.models.review import ReviewResponse


class HtmlReportService:
    def __init__(self, template_directory: Path | None = None) -> None:
        base_dir = Path(__file__).resolve().parents[2]
        templates_dir = template_directory or base_dir / "templates"
        self._environment = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate(self, response: ReviewResponse) -> str:
        template = self._environment.get_template("review_report.html")
        return template.render(response=response)
