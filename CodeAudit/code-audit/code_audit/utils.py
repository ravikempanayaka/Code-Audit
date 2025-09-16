# reports/utils.py
import os
from pathlib import Path

class DjangoCodeAudit:
    def __init__(self, file_author=None):
        self.file_author = file_author
        self.home = str(Path.home())

    def run_pylint(self, target, output_name):
        """Run pylint for target and generate html"""
        output_path = os.path.join(self.home, f"{output_name}_report.html")
        cmd = f"pylint {target} | pylint_report > {output_path}"
        os.system(cmd)
        return output_path

    def run_module_report(self, module_path):
        """Generate report for a whole module"""
        return self.run_pylint(module_path, Path(module_path).name)

    def run_api_reports(self, app_path):
        """Generate report for all APIs inside an app"""
        report_files = []
        api_path = os.path.join(app_path, "api")
        if os.path.exists(api_path):
            for f in os.listdir(api_path):
                if f.endswith(".py") and not f.startswith("__"):
                    file_path = os.path.join(api_path, f)
                    report_files.append(self.run_pylint(file_path, Path(f).stem))
        return report_files

    def run_view_reports(self, app_path):
        """Generate report for all views.py files"""
        report_files = []
        for root, dirs, files in os.walk(app_path):
            for f in files:
                if f == "views.py":
                    file_path = os.path.join(root, f)
                    report_files.append(self.run_pylint(file_path, Path(root).name + "_views"))
        return report_files
