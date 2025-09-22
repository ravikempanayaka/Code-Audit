import datetime
import importlib
import logging
import os
import subprocess
from optparse import OptionParser
from pathlib import Path

from django.conf import settings

LOGGER = logging.getLogger(__name__)
home = str(Path.home())


class CodeAuditError(Exception):
    """Custom exception for CodeAudit errors."""


class CodeAudit:
    """Generate report based on cmd args"""

    def __init__(self, *args, **kwargs):
        self.log = None
        self.file_author = None
        self.file_name = None
        self.html_output_file_path = None
        self.json_output_file_path = None
        self.git_user = None

    def parse(self):
        parser = OptionParser()
        self.add_parser_options(parser)
        self.options, args = parser.parse_args()
        self.init()

    @staticmethod
    def add_parser_options(parser):
        parser.add_option("-d", "--debug", dest="debug", help="Debug logs",
                          default=False, action='store_true')
        parser.add_option('--file-name', dest='file_name', type=str, help='specify the file name')
        parser.add_option('--file-author', dest='file_author', type=str, help='specify file author')
        parser.add_option('--output-filepath', dest='output_filepath',
                          type=str, help='specify the html output filepath')
        parser.add_option(
            "--git-user", "-u",
            nargs="?",  # optional value
            const=True,  # if provided without value
            help="Git username/email to filter files. If no value is given, uses current git config user.name"
        )
        return parser

    def init(self):
        self.file_name = self.options.file_name
        self.file_author = self.options.file_author
        self.html_output_file_path = self.options.output_filepath
        self.git_user = self.options.git_user

    def process(self):
        """get report based on cmd args"""
        try:
            html_format = '.html'
            app_list = self.get_django_project_apps()
            if self.file_name:
                # validate file exists
                if not os.path.exists(self.file_name):
                    app, relative_path = self.get_app_from_file(self.file_name, app_list)
                    if app:
                        self.file_name = os.path.join(app, relative_path)
                    if not os.path.exists(self.file_name):
                        file_list = self.find_file_in_apps(self.file_name, app_list)
                        if file_list:
                            print("File list: ", len(file_list))
                            self.file_name = " ".join(file_list)

                        else:
                            if not self.file_name.endswith('.py'):
                                dir_list = self.find_dir_in_apps(self.file_name, app_list)
                                if dir_list:
                                    print("Directory list: ", len(dir_list))
                                    self.file_name = " ".join(dir_list)
                                else:
                                    raise FileNotFoundError(f"File not found: {self.file_name}")
                            else:
                                raise FileNotFoundError(f"File not found: {self.file_name}")

                print("File to audit: ", self.file_name)
                file_name = self.file_name.split('.')[0].split('/')
                default_file_name = ' '.join(file_name).split()[-1:][0]

                if not self.html_output_file_path:
                    self.html_output_file_path = os.path.join(home, default_file_name + html_format)
                print("Output report path: ", self.html_output_file_path)
                print("Generating report...")
                self.generate_json_html_report(
                    self.file_name,
                    self.html_output_file_path
                )
                print("Report generated at: ", self.html_output_file_path)
            else:
                print("Generate Report from app level")
                self.generate_report_app_wise(app_list)

        except Exception as e:
            LOGGER.exception("Error while processing CodeAudit")
            raise CodeAuditError(f"Code audit failed: {e}") from e

    def get_git_username(self):
        """Return the configured git username from local repo."""
        try:
            return subprocess.check_output(
                ["git", "config", "user.name"], text=True
            ).strip()
        except subprocess.CalledProcessError:
            return None

    def filter_by_file(self, file):
        if file.strip() and '.py' in file.strip() and not os.path.basename(file).startswith(
                "__") and not os.path.basename(file).startswith("000"):
            return True
        else:
            return False

    def get_files_changed_by_user(self, user, app_list):
        cmd = f'git log --author="{user}" --name-only --pretty=format:'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        # Split lines, remove empties, and unique them
        files = sorted(set(
            self.get_app_from_file(line.strip(), app_list, is_join=True) for line in result.stdout.splitlines() if
            self.filter_by_file(line)))
        return files

    def generate_report_app_wise(self, app_list: list[str]):
        """Generate reports for all files inside an app."""
        file_list = []
        html_format = '.html'
        if not self.file_name:
            self.file_name = ''
        username = None
        if self.git_user:
            if self.git_user is True:  # --git-user used without value
                username = self.get_git_username()
            elif self.git_user:
                username = self.git_user

        for app in app_list:
            module = importlib.import_module(app)
            app_path = Path(module.__file__).resolve()
            if app_path.exists():
                print("App path exist!")
                for root, dirs, files in os.walk(app_path.parent):
                    if self.file_author:
                        print("Report Generating at Author level")
                        file_list.extend(self.get_file_author_file(root, files))
                    elif username:
                        file_list.extend(self.get_files_changed_by_user(username, app_list))
                    else:
                        for f in files:
                            if f.endswith(".py") and not f.startswith("__") and not f.startswith("000"):
                                file_path = os.path.join(root, f)
                                file_list.append(file_path)
        print("Len of file list: ", len(file_list))
        sorted(set())
        if file_list:
            self.file_name = " ".join(file_list)
        else:
            LOGGER.error(f"No Py files are in this project")
            raise CodeAuditError(f"Code audit failed")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_file_name = self.file_author + f"_{timestamp}" if self.file_author else "app_level_report_" + timestamp

        if not self.html_output_file_path:
            self.html_output_file_path = os.path.join(home, default_file_name + html_format)
        print("Output report path: ", self.html_output_file_path)
        print("Generating report...")
        self.generate_json_html_report(
            self.file_name,
            self.html_output_file_path
        )
        print("Report generated at: ", self.html_output_file_path)

    def get_file_author_file(self, root, files):
        """get author specific file list"""
        file_list = []
        matches = [f"current maintainer: {self.file_author}", f"author: {self.file_author}"]
        print("Matches: ", matches)
        try:
            for f in files:
                if f.endswith(".py") and not f.startswith("__") and not f.startswith("000"):
                    file_path = os.path.join(root, f)
                    try:
                        with open(file_path, "r", encoding="utf-8") as fh:
                            file_str = fh.read()
                            if any(x in file_str for x in matches):
                                file_list.append(file_path)
                    except (FileNotFoundError, OSError) as fe:
                        LOGGER.warning("Could not read file %s: %s", file_path, fe)
        except Exception as e:
            LOGGER.exception("Error scanning directory: %s", files)
        return file_list

    def get_pylintrc_file(self):
        """
        :return:
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if getattr(settings, 'CODE_AUDIT', {}):
            code_audit = getattr(settings, 'CODE_AUDIT', {})
            default_pylintrc = code_audit.get("DEFAULT_PYLINTRC", False)
            if not default_pylintrc:
                pylintrc = code_audit.get("PYLINTRC_PATH", '')
                if not pylintrc:
                    pylintrc = os.path.join(base_dir, "pylintrc")
                    return pylintrc
        pylintrc = os.path.join(base_dir, "pylintrc")
        return pylintrc



    def generate_json_html_report(self, file_name, html_output_file_path):
        """generate json and html report in specific path"""
        try:
            pylintrc = self.get_pylintrc_file()

            if not os.path.exists(pylintrc):
                raise FileNotFoundError(f"pylintrc not found at {pylintrc}")

            cmd = f"pylint --rcfile {pylintrc} {file_name} | pylint_report > {html_output_file_path}"
            LOGGER.info("Running command: %s", cmd)

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode not in (0, 32):  # pylint returns 32 if no files
                LOGGER.error("Pylint failed: %s", result.stderr.strip())
                raise CodeAuditError(f"Pylint failed for {file_name}")

        except Exception as e:
            LOGGER.exception("Error generating report for %s", file_name)
            raise

    def get_django_project_apps(self, relative_path=False):
        """Retrieve Django project apps from settings."""
        import importlib
        from pathlib import Path
        import site
        from django.conf import settings

        SITE_PACKAGES = site.getsitepackages()

        def is_in_site_packages(path: Path) -> bool:
            return any(str(path).startswith(sp) for sp in SITE_PACKAGES)

        project_apps = []
        third_party_apps = []

        for app in settings.INSTALLED_APPS:
            try:
                module = importlib.import_module(app)
                app_path = Path(module.__file__).resolve()

                if is_in_site_packages(app_path):
                    third_party_apps.append(app)
                else:
                    project_apps.append(app)
            except Exception:
                third_party_apps.append(app)
        return project_apps

    @staticmethod
    def get_app_from_file(file_name: str, project_apps: list[str], is_join: bool = False):
        """
        Extract the app name and relative file path from a given file path.

        Args:
            file_name (str): Full path to the file.
            project_apps (list[str]): List of valid Django app names in the project.
            is_join (bool, optional): If True, return "app/relative_path" instead of a tuple.
                                      Defaults to False.

        Returns:
            tuple[str, str] | str | None:
                - (app_name, relative_path) if matched and `is_join=False`.
                - "app/relative_path" if matched and `is_join=True`.
                - ("", "") or "" if ignored (e.g. migrations).
                - (None, None) if no match found.
        """
        path = Path(file_name)
        parts = path.parts

        # Ignore migration files
        if "migrations" in parts:
            return "" if is_join else (None, None)

        # Find first app in the path
        for app in project_apps:
            if app == "code_audit":  # explicitly ignore self-app
                continue

            if app in parts:
                idx = parts.index(app)
                app_name = app
                relative_path = Path(*parts[idx + 1:])  # inside app

                result = os.path.join(app, str(relative_path)) if is_join else (app_name, str(relative_path))
                return result

        # No matching app
        return "" if is_join else (None, None)

    def find_file_in_apps(self, filename: str, apps: list[str]) -> list[str]:
        """
        Search for a file by name across all project apps.

        :param filename: file name to search (e.g., 'views.py', 'serializers.py')
        :param apps: list of project apps
        :return: list of matching file paths
        """
        matches = []
        base_dir = Path(settings.BASE_DIR)
        print(base_dir)
        for app in apps:
            module = importlib.import_module(app)
            app_path = Path(module.__file__).resolve()
            if app_path.exists():

                for root, dirs, files in os.walk(app_path.parent):
                    if filename in files:
                        matches.append(str(Path(root) / filename))
        return matches

    def find_dir_in_apps(self, dir_name: str, apps: list[str]) -> list[str]:
        """
        Search for a directory by name across all project apps.

        :param dir_name: directory name to search (e.g., 'api', 'views')
        :param apps: list of project apps
        :return: list of matching directory paths
        """
        matches = []
        for app in apps:
            module = importlib.import_module(app)
            app_path = Path(module.__file__).resolve()
            if app_path.exists():
                for root, dirs, files in os.walk(app_path.parent):
                    if dir_name in dirs:
                        matches.append(str(Path(root) / dir_name))
        return matches

    def get_dirs_in_apps(self, apps: list[str]) -> list[str]:
        """
        Get all directories inside project apps.

        :param apps: list of project apps
        :return: list of directory paths
        """
        dir_list = []
        for app in apps:
            module = importlib.import_module(app)
            app_path = Path(module.__file__).resolve()
            if app_path.exists():
                for root, dirs, files in os.walk(app_path.parent):
                    for dir in dirs:
                        if dir != "migrations":
                            dir_list.append(str(Path(root) / dir))
        return dir_list
