# reports/admin_urls.py
from django.urls import path
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from ..models import CodeAuditReport

def run_audit(request, pk):
    report = get_object_or_404(CodeAuditReport, pk=pk)
    report.run_audit(level="file")  # process() handles it
    return redirect("/admin/reports/codeauditreport/")

def view_audit_report(request, pk):
    report = get_object_or_404(CodeAuditReport, pk=pk)
    file_idx = int(request.GET.get("file", 0))
    reports = report.report_path.split(",") if report.report_path else []
    if reports and file_idx < len(reports):
        with open(reports[file_idx]) as f:
            return HttpResponse(f.read())
    return HttpResponse("No report available")

urlpatterns = [
    path("run/<int:pk>/", run_audit, name="run_audit"),
    path("view/<int:pk>/", view_audit_report, name="view_audit_report"),
]
