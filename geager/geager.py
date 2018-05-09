#! /usr/bin/env python
#
#   geager.py -- Front-end script for running Singularity EAGER over
#   over an arbitrary number of subjects.
#
#   Copyright (C) 2018, 2019 S3IT, University of Zurich
#
#   This program is free software: you can redistribute it and/or
#   modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Front-end script for submitting multiple `EAGER apps` subject analysis.
see: http://eager.readthedocs.io/en/latest/contents/installation.html#singularity

It uses the generic `gc3libs.cmdline.SessionBasedScript` framework.

See the output of ``geager.py --help`` for program usage
instructions.
"""

# summary of user-visible changes
__changelog__ = """
  2018-04-09:
  * Initial version
"""
__author__ = 'Sergio Maffioletti <sergio.maffioletti@uzh.ch>'
__docformat__ = 'reStructuredText'
__version__ = '1.0'

import os

import gc3libs
import gc3libs.exceptions
from gc3libs import Application
from gc3libs.cmdline import SessionBasedScript, existing_directory
import gc3libs.utils

DEFAULT_DATA_FOLDER = "$PWD/data"
DEFAULT_CONTAINER_APP = "shub://apeltzer/EAGER-GUI"
RUN_EAGER = "singularity exec -B {data_folder}:{data_folder} {container} eagercli {subject_config}"
# singularity exec -B /data/:/data/  ~/apeltzer-EAGER-GUI-master-latest.simg eagercli /data/eagertest_for_sergio/eager_output/ARLP_62/2018-04-30-07-19-EAGER_s3it.xml


# Utility methods


def _get_subjects_config(input_folder):
    """
    Return list of valid input folder:
    Each folder containing a valid .xml eager config file
    """

    subjects = []

    for sbj in os.listdir(input_folder):
        for f in os.listdir(os.path.join(input_folder, sbj)):
            if f.endswith(".xml"):
                subjects.append((os.path.abspath(os.path.join(input_folder,
                                                              sbj)),
                                 f))
                continue
    return subjects


# custom application class


class GeagerApplication(Application):
    """
    Custom class to wrap the execution of the R scripts passed in src_dir.
    """

    application_name = 'geager'

    def __init__(self, data_folder, subject_name, subject_config, **extra_args):
        """
        Input and Output should be available through  a locally mounted
        shared filesystem
        e.g. /data
        """

        inputs = {}

        if extra_args['transfer_data'] == True:
            # All input data need to be transferred
            inputs[data_folder] = DEFAULT_DATA_FOLDER
            data_folder = DEFAULT_DATA_FOLDER

            inputs[subject_config] = ""

        arguments = RUN_EAGER.format(data_folder=data_folder,
                                     container=DEFAULT_CONTAINER_APP,
                                     subject_config=subject_config)
        gc3libs.log.debug("Creating application for executing: %s", arguments)

        Application.__init__(
            self,
            arguments=arguments,
            inputs=inputs,
            outputs=gc3libs.ANY_OUTPUT,
            stdout='{0}.log'.format(subject_name),
            join=True,
            **extra_args)


class GeagerScript(SessionBasedScript):
    """
    The ``geager`` command keeps a record of jobs (submitted, executed
    and pending) in a session file (set name with the ``-s`` option); at
    each invocation of the command, the status of all recorded jobs is
    updated, output from finished jobs is collected, and a summary table
    of all known jobs is printed.

    Options can specify a maximum number of jobs that should be in
    'SUBMITTED' or 'RUNNING' state; ``geager`` will delay submission of
    newly-created jobs so that this limit is never exceeded.

    Once the processing of all chunked files has been completed, ``geager``
    aggregates them into a single larger output file located in
    'self.params.output'.
    """

    def __init__(self):
        SessionBasedScript.__init__(
            self,
            version=__version__,
            application=GeagerApplication,
            stats_only_for=GeagerApplication,
        )

    def setup_args(self):
        self.add_param('input_folder',
                       type=existing_directory,
                       help="Path to input folder containing valid input .bids files.")

    def setup_options(self):
        self.add_param("-F", "--datatransfer", dest="transfer_data",
                       action="store_true", default=False,
                       help="Transfer input data to compute nodes. "
                            "If False, data will be assumed be already visible on "
                            "compute nodes - e.g. shared filesystem. "
                            "Default: %(default)s.")

    def parse_args(self):
        self.params.input_folder = os.path.abspath(self.params.input_folder)

    def new_tasks(self, extra):
        """
        For each valid input file create a new geagerApplication
        """
        tasks = []

        for (subject, subject_config_file) in _get_subjects_config(self.params.input_folder):
            subject_name = os.path.basename(subject)

            job_name = "{0}".format(subject_name)
            extra_args = extra.copy()
            extra_args['jobname'] = job_name
            extra_args['transfer_data'] = self.params.transfer_data
            extra_args['output_dir'] = self.params.output.replace('NAME',
                                                                  os.path.join('.compute',
                                                                               job_name))

            self.log.debug("Creating Application for subject {0}".format(subject_name))

            tasks.append(GeagerApplication(
                self.params.input_folder,
                subject_name,
                subject_config_file,
                **extra_args))

        return tasks


# run script, but allow GC3Pie persistence module to access classes defined here;
# for details, see: http://code.google.com/p/gc3pie/issues/detail?id=95
if __name__ == "__main__":
    import geager

    geager.GeagerScript().run()
