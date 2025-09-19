# reports/admin_urls.py
import logging
import os
from django.urls import path
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from ..models import CodeAuditReport

logger = logging.getLogger(__name__)


def run_audit(request, pk):
    """Trigger a code audit run for the given report."""
    try:
        report = get_object_or_404(CodeAuditReport, pk=pk)
        report.run_audit(level="file")  # process() handles it
        return redirect("/admin/reports/codeauditreport/")
    except Exception as e:
        logger.exception(f"Error while running audit for report {pk}: {e}")
        return HttpResponse("An error occurred while running the audit.", status=500)


def view_audit_report(request, pk):
    """Render a stored audit report, with optional ?file=N selection."""
    try:
        report = get_object_or_404(CodeAuditReport, pk=pk)

        if not report.report_path:
            logger.warning(f"No report_path set for report {pk}")
            return HttpResponse("No report available", status=404)

        reports = report.report_path.split(",")
        file_idx = int(request.GET.get("file", 0))

        if file_idx < 0 or file_idx >= len(reports):
            logger.error(
                f"Invalid file index {file_idx} requested for report {pk}. Available: {len(reports)}"
            )
            raise Http404("Invalid report file index.")

        file_path = reports[file_idx]
        if not os.path.isfile(file_path):
            logger.error(f"Report file missing at {file_path} for report {pk}")
            return HttpResponse("Report file not found", status=404)

        with open(file_path, encoding="utf-8") as f:
            return HttpResponse(f.read())

    except Http404 as e:
        raise e  # let Django handle 404 properly
    except Exception as e:
        logger.exception(f"Error while viewing audit report {pk}: {e}")
        return HttpResponse("An error occurred while retrieving the report.", status=500)


urlpatterns = [
    path("run/<int:pk>/", run_audit, name="run_audit"),
    path("view/<int:pk>/", view_audit_report, name="view_audit_report"),
]
