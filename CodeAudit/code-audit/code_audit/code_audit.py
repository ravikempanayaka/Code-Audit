"""
Code Audit Report script
current maintainer: ravi.k
"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(1, os.getcwd())

from optparse import OptionParser

from django.conf import settings

LOGGER = logging.getLogger(__name__)

home = str(Path.home())


class CodeAudit:
    """Generate report based on cmd args"""

    def __init__(self, *args, **kwargs):
        """initialize variables"""
        self.log = None
        self.file_author = None
        self.file_name = None
        self.html_output_file_path = None
        self.json_output_file_path = None

    def parse(self):
        parser = OptionParser()
        self.add_parser_options(parser)
        (self.options, args) = parser.parse_args()
        self.init()

    @staticmethod
    def add_parser_options(parser):
        parser.add_option("-d", "--debug", dest="debug", help="Debug logs",
                          default=False, action='store_true'
                          )
        parser.add_option('--file-name', dest='file_name', type=str, help='specify the file name'
                          )
        parser.add_option('--file-author', dest='file_author', type=str, help='specify file author'
                          )
        parser.add_option('--output-filepath', dest='output_filepath',
                          type=str, help='specify the html output filepath'
                          )
        return parser

    def init(self):
        self.file_name = self.options.file_name
        self.file_author = self.options.file_author
        self.html_output_file_path = self.options.output_filepath

    def process(self):
        """get report based on cmd args"""
        html_format = '.html'

        # check file name passed in cmd if exist generate report based on file name else condition
        if self.file_name:
            file_name = self.file_name.split('.')[0].split('/')
            default_file_name = ' '.join(file_name).split()[-1:][0]
            if not self.html_output_file_path:
                self.html_output_file_path = home + '/' + default_file_name + html_format

            self.generate_json_html_report(
                self.file_name,
                self.html_output_file_path
            )
        else:
            file_name = None
            # Application List
            for app in settings.APP_LIST:
                file_path_list = list()
                for root, dirs, files in os.walk(app):
                    if root in [app + "/" + "api"]:
                        file_name = root + '/'
                        if self.file_author:
                            author_file_list = self.get_file_author_file(root)
                            if len(author_file_list):
                                for at_file in author_file_list:
                                    file_path_list.append(at_file)
                        break

                if self.html_output_file_path:
                    html_obj_list = self.html_output_file_path.split('.')
                    html_file_name = html_obj_list[0] + '_' + app + '.' + html_obj_list[1]
                else:
                    html_file_name = home + '/' + app + html_format

                # check if file author in args
                if self.file_author or len(file_path_list):
                    for file_path in file_path_list:
                        file_path_name = home + '/' + file_path.split('.')[0].split('/')[-1:][0]
                        html_file_name = file_path_name + html_format
                        self.generate_json_html_report(file_path, html_file_name)

                else:
                    self.generate_json_html_report(file_name, html_file_name)

    def get_file_author_file(self, file_dir):
        """get author specific file list
        parameters:
            :file_dir- search name in this dir
        return:
            list of file path
        """
        file_list = list()
        matches = ["current maintainer: " + self.file_author, "author: " + self.file_author]
        for root, dirs, files in os.walk(file_dir):
            for f in files:
                if f.endswith(".py") and not f.startswith("__"):
                    file_str = open(root + "/" + f, "r").read()
                    if any(x in file_str for x in matches):
                        file_list.append(root + "/" + f)
        return file_list

    @staticmethod
    def generate_json_html_report(file_name, html_output_file_path):
        """generate json and html report in specific path
        parameters:
            :file_name- specific files or app name
            :html_output_file_path - mention path to store
        return:
            None
        """
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        print("BASE_DIR:", BASE_DIR)
        # base_dir = os.getcwd() + '/code_audit'
        pylintrc = os.path.join(BASE_DIR, "pylintrc")
        param1 = 'pylint ' + f'--rcfile {pylintrc} ' + file_name + '|' + 'pylint_report  > ' + html_output_file_path
        os.system(param1)

# if __name__ == '__main__':
#     standalone_main(CodeAudit)
