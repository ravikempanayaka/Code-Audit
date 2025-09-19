import logging
import os

from django.contrib import admin, messages
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Subquery, OuterRef
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from .models import CodeAuditReport, CodeAuditReportLog

LOGGER = logging.getLogger(__name__)


class CodeAuditReportLogInline(admin.TabularInline):
    model = CodeAuditReportLog
    extra = 0
    readonly_fields = ("pylint_score", "report_path", "run_at")


class CodeAuditReportAdmin(admin.ModelAdmin):
    list_display = (
        "id", "module_name", "file_name", "status", "created_at",
        "last_score_display", "pylint_score",
        "run_report_link", "view_report_link", "all_scores_display"
    )
    list_filter = ("module_name", "status", "created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        last_log = CodeAuditReportLog.objects.filter(
            report=OuterRef("pk")
        ).order_by("-run_at")

        qs = qs.annotate(
            last_score_annotated=Subquery(last_log.values("pylint_score")[:1]),
            all_scores_annotated=ArrayAgg("logs__pylint_score", distinct=False),
        )
        return qs

    def last_score_display(self, obj):
        return obj.last_score_annotated

    last_score_display.admin_order_field = "last_score_annotated"
    last_score_display.short_description = "Last Score"

    def all_scores_display(self, obj):
        if obj.all_scores_annotated:
            return ", ".join(str(s) for s in obj.all_scores_annotated)
        return "-"

    all_scores_display.short_description = "All Scores"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("run/<int:pk>/", self.admin_site.admin_view(self.run_audit), name="run_audit"),
            path("view/<int:pk>/", self.admin_site.admin_view(self.view_audit_report), name="view_audit"),
        ]
        return custom_urls + urls

    def run_report_link(self, obj):
        return format_html('<a href="{}">Run Report</a>', f"run/{obj.pk}/")

    run_report_link.short_description = "Run"

    def view_report_link(self, obj):
        return format_html('<a href="{}">View Report</a>', f"view/{obj.pk}/")

    view_report_link.short_description = "View"

    # Run audit
    def run_audit(self, request, pk):
        try:
            report = get_object_or_404(CodeAuditReport, pk=pk)
            report.run_audit(level="file")
            messages.success(request, f"Audit successfully triggered for {report.file_name}")
        except Exception as e:
            LOGGER.exception("Failed to run audit for report %s", pk)
            messages.error(request, f"❌ Failed to run audit: {str(e)}")

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))

    # View audit
    def view_audit_report(self, request, pk):
        report = get_object_or_404(CodeAuditReport, pk=pk)

        if not report.report_path:
            messages.warning(request, "⚠️ Report path missing. Try regenerating the audit.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))

        file_path = report.report_path.split(",")[0]  # first report

        if not file_path or not os.path.isfile(file_path):
            LOGGER.warning("Report file not found: %s", file_path)

            if "generate" in request.GET:
                try:
                    report.run_audit(level="file")
                    messages.info(request, "⚡ Report not found. A new audit has been triggered.")
                    return HttpResponseRedirect(reverse("view_audit_report", args=[report.id]))
                except Exception as e:
                    LOGGER.exception("Error regenerating report for %s", pk)
                    return HttpResponse(f"Error regenerating report: {str(e)}", status=500)

            return HttpResponse(self._render_report_not_found(), status=404)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return HttpResponse(f.read())
        except FileNotFoundError:
            LOGGER.error("File missing during view attempt: %s", file_path)
            return HttpResponse("Report file not found", status=404)
        except PermissionError:
            LOGGER.error("Permission denied accessing report: %s", file_path)
            return HttpResponse("Permission denied accessing report", status=403)
        except Exception as e:
            LOGGER.exception("Unexpected error opening report %s", file_path)
            return HttpResponse(f"Unexpected error: {str(e)}", status=500)

    @staticmethod
    def _render_report_not_found():
        """Render styled HTML page when report is missing."""
        return """
            <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; background: #f4f6f9; text-align: center; padding: 50px; }
                        .error-box {
                            background: white; padding: 40px; border-radius: 15px;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.1); display: inline-block;
                            animation: fadeIn 1s ease-in-out;
                        }
                        h1 { font-size: 80px; margin: 0; color: #ff4757; }
                        h2 { margin: 10px 0; color: #2f3542; }
                        p { color: #57606f; }
                        .btn {
                            display: inline-block; margin-top: 20px; padding: 12px 24px;
                            background: #3742fa; color: white; text-decoration: none;
                            border-radius: 8px; transition: 0.3s;
                        }
                        .btn:hover { background: #2f3542; }
                        @keyframes fadeIn { from {opacity: 0;} to {opacity: 1;} }
                    </style>
                </head>
                <body>
                    <div class="error-box">
                        <h1>404</h1>
                        <h2>Report Not Found</h2>
                        <p>Oops! The requested audit report could not be located.<br>
                           It might have been moved, deleted, or never generated.</p>
                        <a href="?generate=1" class="btn">⚡ Generate Now</a>
                        <a href="/admin/code_audit/codeauditreport/" class="btn">🔙 Back to Reports</a>
                    </div>
                </body>
            </html>
        """


admin.site.register(CodeAuditReport, CodeAuditReportAdmin)
