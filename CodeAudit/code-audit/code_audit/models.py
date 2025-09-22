# reports/models.py
import datetime
import logging
import os
import re

from django.db import models
from django.utils import timezone

from .code_audit import CodeAudit  # reuse your class

logger = logging.getLogger(__name__)


class CodeAuditReport(models.Model):
    module_name = models.CharField(max_length=255, help_text='filter module name')
    file_name = models.CharField(max_length=255, blank=True, null=True, help_text="Python file or app to audit")
    file_author = models.CharField(max_length=100, blank=True, null=True)
    git_user = models.CharField(max_length=100, blank=True, null=True)
    last_run = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=50, default="Not Run")
    report_path = models.TextField(blank=True, null=True, default='/tmp/')  # can store multiple reports
    pylint_score = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Audit: {self.file_name} ({self.status})"

    def run_audit(self, level="file"):
        """Run audit via CodeAudit.process() with error handling."""
        audit = CodeAudit()
        audit.file_name = self.file_name if level == "file" else None
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        audit.output_filepath = f"/tmp/{self.module_name}_{level}_audit_{timestamp}.html"
        audit.file_author = self.file_author
        audit.html_output_file_path = None  # let CodeAudit decide
        reports = []
        pylint_score = 0.0

        try:
            # Run the actual audit
            audit.process()

            # Collect outputs from process
            if audit.html_output_file_path:
                reports.append(audit.html_output_file_path)
                output_file_path = audit.html_output_file_path

                if os.path.isfile(output_file_path):
                    try:
                        with open(output_file_path, "r", encoding="utf-8") as f:
                            html_content = f.read()

                        # Extract pylint score using regex
                        match = re.search(
                            r'<span class="score">\s*([0-9.]+)\s*</span>',
                            html_content,
                        )
                        if match:
                            pylint_score = float(match.group(1))
                    except Exception as e:
                        logger.error(f"Failed to read or parse report file {output_file_path}: {e}")
                else:
                    logger.warning(f"Report file does not exist: {output_file_path}")

        except Exception as e:
            logger.exception(f"Audit process failed for {self.file_name}: {e}")
            self.status = "Failed"
            self.save(update_fields=["status", "updated_at"])
            return []

        # Save results
        self.report_path = ",".join(reports) if reports else None

        # Log previous score if available
        if self.pylint_score:
            CodeAuditReportLog.objects.create(
                report=self,
                pylint_score=self.pylint_score,
                report_path=self.report_path or "",
            )

        self.pylint_score = pylint_score
        self.last_run = timezone.now()
        self.status = "Completed" if reports else "Failed"
        self.save()

        return reports


class CodeAuditReportLog(models.Model):
    report = models.ForeignKey(CodeAuditReport, on_delete=models.CASCADE, related_name="logs")
    pylint_score = models.FloatField()
    report_path = models.TextField()
    run_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-run_at"]

    def __str__(self):
        return f"{self.report.file_name} - {self.pylint_score} ({self.run_at:%Y-%m-%d %H:%M})"
