import datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from .code_audit_by_commend import CodeAudit


class Command(BaseCommand):
    help = "Run code quality checks using django-code-audit"

    def __init__(self):
        super().__init__()
        self.audit = CodeAudit()

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Specific file path to check'
        )
        parser.add_argument(
            '--file-author',
            type=str,
            help='Specify file author (for pylint configuration)'
        )
        parser.add_argument(
            '--fail-under',
            type=float,
            default=8.0,
            help='Minimum score required to pass the audit'
        )
        parser.add_argument(
            "--git-user", "-u",
            nargs="?",  # optional value
            const=True,  # if provided without value
            help="Git username/email to filter files. If no value is given, uses current git config user.name"
        )

    def handle(self, *args, **options):
        file_path = options.get('file')
        file_author = options.get('file_author')
        git_user = options.get('git_user')
        fail_under = options['fail_under']

        if file_path:
            target = file_path
        else:
            target = "your_app/"  # default full project

        self.stdout.write(f"🔎 Auditing: {target}")
        base_dir = 'general_search'
        if file_path:
            path_obj = Path(file_path)
            base_dir = path_obj.parts[0] if path_obj.parts else file_path

        try:
            pylint_score = self.run_audit(file_path, base_dir, level="file", file_author=file_author,
                                          git_user=git_user)
        except Exception as ex_err:
            self.stderr.write(self.style.ERROR(
                f"❌ An unexpected error occurred: {ex_err}"
            ))
            return None

        # Extract score from pylint report
        # (or use your existing logic)
        score = pylint_score if pylint_score else 0.0

        if score < fail_under:
            self.stderr.write(self.style.ERROR(
                f"❌ Audit failed. Score {score} < {fail_under}"
            ))
            exit(1)
        else:
            self.stdout.write(self.style.SUCCESS(
                f"✅ Audit passed. Score {score}"
            ))
            return str(score)

    def run_audit(self, file_path, module_name, level="file", file_author=None, git_user=False):
        """Run audit via CodeAudit.process()"""
        # audit = CodeAudit()
        self.audit.file_name = file_path if level == "file" else None
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.audit.output_filepath = f"/tmp/{module_name}_{level}_audit_{timestamp}.html"
        self.audit.file_author = file_author
        self.audit.git_user = git_user
        self.audit.html_output_file_path = None  # let CodeAudit decide
        reports = []

        # Call process (this generates reports based on setup)
        self.audit.process()

        # Collect outputs from process
        if self.audit.html_output_file_path:
            reports.append(self.audit.html_output_file_path)

        output_file_path = self.audit.html_output_file_path
        if isinstance(output_file_path, list):
            score = 0.0
            for output_path in output_file_path:
                # Extract score from HTML
                with open(output_path, "r") as f:
                    html_content = f.read()
                pylint_score = 0
                import re
                match = re.search(r'<span class="score">\s*([0-9.]+)\s*</span>', html_content)
                if match:
                    pylint_score = float(match.group(1))
                    print(pylint_score)
                    score += pylint_score
            pylint_score = score / len(output_file_path) if len(output_file_path) else 0.0
        else:
            # Extract score from HTML
            with open(output_file_path, "r") as f:
                html_content = f.read()
            pylint_score = 0
            import re
            match = re.search(r'<span class="score">\s*([0-9.]+)\s*</span>', html_content)
            if match:
                pylint_score = float(match.group(1))
                print(pylint_score)
        return pylint_score
