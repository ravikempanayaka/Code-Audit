import datetime
import importlib
import logging
import os
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
        return parser

    def init(self):
        self.file_name = self.options.file_name
        self.file_author = self.options.file_author
        self.html_output_file_path = self.options.output_filepath

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
                            # self.generate_json_html_report(
                            #     file_list,
                            #     self.html_output_file_path or os.path.join(home, 'multiple_files_report' + html_format)
                            # )
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

    def generate_report_app_wise(self, app_list: list[str]):
        """Generate reports for all files inside an app."""
        file_list = []
        html_format = '.html'
        if not self.file_name:
            self.file_name = ''

        for app in app_list:
            module = importlib.import_module(app)
            app_path = Path(module.__file__).resolve()
            if app_path.exists():
                print("App path exist!")
                for root, dirs, files in os.walk(app_path.parent):
                    if self.file_author:
                        print("Report Generating at Author level")
                        file_list.extend(self.get_file_author_file(root, files))
                    else:
                        for f in files:
                            if f.endswith(".py") and not f.startswith("__") and not f.startswith("000"):
                                file_path = os.path.join(root, f)
                                file_list.append(file_path)
        print("Len of file list: ", len(file_list))
        if file_list:
            self.file_name = " ".join(file_list)
        else:
            LOGGER.error(f"No Py files are in this project")
            raise CodeAuditError(f"Code audit failed")
        print("File Name: ", self.file_name)
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

    @staticmethod
    def generate_json_html_report(file_name, html_output_file_path):
        """generate json and html report in specific path"""
        try:
            app_dir = Path(__file__).resolve().parent.parent.parent
            pylintrc = app_dir / "pylintrc"

            if not pylintrc.exists():
                print(f"Error: pylintrc file not found at {pylintrc}")
                return
            # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            # # base_dir = os.getcwd() + '/code_audit'
            # pylintrc = os.path.join(BASE_DIR, "pylintrc")
            param1 = 'pylint ' + f'--rcfile {pylintrc} ' + file_name + '|' + 'pylint_report  > ' + html_output_file_path
            os.system(param1)
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

    def get_app_from_file(self, file_name: str, project_apps: list[str]) -> tuple[str, str]:
        """
        Given a file path, return (app_name, relative_file_path_within_app).
        Example: backend/comp_restore/api/views/chat.py -> ("comp_restore", "api/views/chat.py")
        """
        path = Path(file_name)

        # Break the path into parts (['backend', 'comp_restore', 'api', 'views', 'chat.py'])
        parts = path.parts

        # Find first matching project app in path
        for app in project_apps:
            if app in parts:
                idx = parts.index(app)
                app_name = app
                relative_path = Path(*parts[idx + 1:])  # everything inside the app
                return app_name, str(relative_path)

        return None, None  # not a project app

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
