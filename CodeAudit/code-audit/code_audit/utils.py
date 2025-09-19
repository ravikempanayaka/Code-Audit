# reports/utils.py
import os
import logging
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)


class DjangoCodeAudit:
    """Utility for running pylint reports in a structured way."""

    def __init__(self, file_author=None):
        self.file_author = file_author
        self.home = str(Path.home())

    def run_pylint(self, target: str, output_name: str) -> str | None:
        """
        Run pylint for a given target and generate an HTML report.

        :param target: Python file/module to lint
        :param output_name: Name prefix for the report
        :return: Path to generated report or None if failed
        """
        try:
            output_path = os.path.join(self.home, f"{output_name}_report.html")
            cmd = f"pylint {target} | pylint_report > {output_path}"
            logger.info(f"Running pylint on {target}, output → {output_path}")

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                logger.warning(
                    f"Pylint finished with errors for {target} (exit code {result.returncode}). "
                    f"stderr: {result.stderr.strip()}"
                )

            if not os.path.isfile(output_path):
                logger.error(f"Report file not generated for {target}.")
                return None

            return output_path
        except Exception as e:
            logger.exception(f"Failed to run pylint on {target}: {e}")
            return None

    def run_module_report(self, module_path: str) -> str | None:
        """Generate report for a whole module."""
        if not os.path.exists(module_path):
            logger.error(f"Module path does not exist: {module_path}")
            return None
        return self.run_pylint(module_path, Path(module_path).name)

    def run_api_reports(self, app_path: str) -> list[str]:
        """Generate reports for all APIs inside an app."""
        report_files = []
        try:
            api_path = os.path.join(app_path, "api")
            if os.path.exists(api_path):
                for f in os.listdir(api_path):
                    if f.endswith(".py") and not f.startswith("__"):
                        file_path = os.path.join(api_path, f)
                        report = self.run_pylint(file_path, Path(f).stem)
                        if report:
                            report_files.append(report)
            else:
                logger.info(f"No API folder found in {app_path}")
        except Exception as e:
            logger.exception(f"Error while running API reports for {app_path}: {e}")
        return report_files

    def run_view_reports(self, app_path: str) -> list[str]:
        """Generate reports for all views.py files."""
        report_files = []
        try:
            for root, dirs, files in os.walk(app_path):
                for f in files:
                    if f == "views.py":
                        file_path = os.path.join(root, f)
                        report = self.run_pylint(file_path, Path(root).name + "_views")
                        if report:
                            report_files.append(report)
        except Exception as e:
            logger.exception(f"Error while running view reports for {app_path}: {e}")
        return report_files
