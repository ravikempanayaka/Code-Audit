# reports/models.py
import datetime

from django.db import models
from django.utils import timezone

from .code_audit import CodeAudit  # reuse your class


class CodeAuditReport(models.Model):
    module_name = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255, help_text="Python file or app to audit")
    file_author = models.CharField(max_length=100, blank=True, null=True)
    last_run = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=50, default="Not Run")
    report_path = models.TextField(blank=True, null=True)  # can store multiple reports
    pylint_score = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)  # <--- Add this
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Audit: {self.file_name} ({self.status})"

    def run_audit(self, level="file"):
        """Run audit via CodeAudit.process()"""
        audit = CodeAudit()
        audit.file_name = self.file_name if level == "file" else None
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        audit.output_filepath = f"/tmp/{self.module_name}_{level}_audit_{timestamp}.html"
        audit.file_author = self.file_author
        audit.html_output_file_path = None  # let CodeAudit decide
        reports = []

        # Call process (this generates reports based on setup)
        audit.process()


        # Collect outputs from process
        if audit.html_output_file_path:
            reports.append(audit.html_output_file_path)

        output_file_path = audit.html_output_file_path
        # Extract score from HTML
        with open(output_file_path, "r") as f:
            html_content = f.read()
        pylint_score = 0
        import re
        match = re.search(r'<span class="score">\s*([0-9.]+)\s*</span>', html_content)
        if match:
            pylint_score = float(match.group(1))
            print(pylint_score)

        # store multiple reports in case module/api/view generated several
        self.report_path = ",".join(reports) if reports else None
        if self.pylint_score:
            log = CodeAuditReportLog.objects.create(
                report=self,
                pylint_score=self.pylint_score,
                report_path=self.report_path
            )
        self.pylint_score = pylint_score
        self.last_run = timezone.now()
        self.status = "Completed" if reports else "Failed"
        self.save()

        return reports

    # @property
    # def last_score(self):
    #     """Quick access to latest pylint score"""
    #     latest_log = self.logs.order_by("-run_at").first()
    #     return latest_log.pylint_score if latest_log else None

    # @property
    # def all_scores(self):
    #     """Comma-separated list of past scores"""
    #     return ", ".join(str(log.pylint_score) for log in self.logs.order_by("-run_at"))


class CodeAuditReportLog(models.Model):
    report = models.ForeignKey(CodeAuditReport, on_delete=models.CASCADE, related_name="logs")
    pylint_score = models.FloatField()
    report_path = models.TextField()
    run_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-run_at"]

    def __str__(self):
        return f"{self.report.file_name} - {self.pylint_score} ({self.run_at:%Y-%m-%d %H:%M})"
