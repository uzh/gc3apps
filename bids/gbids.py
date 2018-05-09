#! /usr/bin/env python
#
#   gbids.py -- Front-end script for running Docker BIDS apps
#   function over a large dataset.
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
Front-end script for submitting multiple `BIDS apps` jobs fetching
docker images from the `BIDS apps` repository.

It uses the generic `gc3libs.cmdline.SessionBasedScript` framework.

See the output of ``gbids.py --help`` for program usage
instructions.

Example of docker execution:
docker run -i --rm -v /mnt/filo/data/ds005:/bids_dataset:ro bids/fmriprep /bids_dataset /outputs participant --participant_label 01

gbids takes BIDS files as input.
"""

# summary of user-visible changes
__changelog__ = """
  2018-01-10:
  * added support for freesurfer license file to be passed as part of the docker invocation. see: https://fmriprep.readthedocs.io/en/latest/installation.html#the-freesurfer-license
  2017-04-18:
  * Initial version
"""
__author__ = 'Sergio Maffioletti <sergio.maffioletti@uzh.ch>'
__docformat__ = 'reStructuredText'
__version__ = '1.0'

import os
import shutil
import subprocess

# GC3Pie specific libraries
import gc3libs
import gc3libs.exceptions
from gc3libs import Application
from gc3libs.workflow import RetryableTask
from gc3libs.cmdline import SessionBasedScript, existing_file, existing_directory
import gc3libs.utils
from gc3libs.quantity import GB

# 3rd-party dependencies
from bids.grabbids import BIDSLayout

# Defaults
MAX_MEMORY = 32*GB
DEFAULT_BIDS_FOLDER = "data/"
DEFAULT_RESULT_FOLDER = "output/"
DEFAULT_DOCKER_BIDS_ARGS = "--no-submm-recon"
DEFAULT_FREESURFER_LICENSE_FILE = "license.txt"
DEFAULT_DOCKER_BIDS_APP = "poldracklab/fmriprep " + DEFAULT_DOCKER_BIDS_ARGS
ANALYSIS_LEVELS = ["participant", "group1", "group2", "group"]
DOCKER_RUN_COMMAND = "sudo docker run -i --rm {DOCKER_MOUNT} {DOCKER_TO_RUN} /bids /output {ANALYSIS} "
COPY_COMMAND = "cp {0}/* {1} -Rf"

# Utility methods


def _get_subjects(root_input_folder):
    """
    build subject list form either input arguments (participant_label, participant_file) or
    (if participant_label and participant_file are not specified) input data in bids_input_folder,
    then remove subjects form list according to participant_exclusion_file (if any)
    """
    layout = BIDSLayout(root_input_folder)
    return [(os.path.abspath(os.path.join(root_input_folder, "sub-{}".format(subject))),
             subject) for subject in layout.get_subjects()]


def _get_control_files(input_folder):
    """
    return tuple ([list .json and .tsv files],[list of sub-folders])
    Assumptions:
    * each sub-folder contains a valid subject's data
    * each .json and .tsv file found in root folder will be made available
    to all Applications.
    """
    return [os.path.abspath(os.path.join(input_folder, control)) for control in os.listdir(input_folder)
            if control.endswith(".json") or control.endswith(".tsv")]


def _is_participant_analysis(analysis_level):
    return analysis_level == ANALYSIS_LEVELS[0]


# Custom application class


class GbidsApplication(Application):
    """
    Custom class to wrap the execution of the R scripts passed in src_dir.
    """
    application_name = 'gbids'

    def __init__(self, docker_run, subject, subject_name, control_files,
                 analysis_level, **extra_args):

        executables = []
        inputs = dict()
        outputs = []

        self.subject_dir = subject
        self.subject_name = subject_name
        self.data_output_dir = extra_args['data_output_dir']

        if extra_args['transfer_data']:
            # Input data need to be transferred to compute node
            # include them in the `inputs` list and adapt
            # container execution command

            if extra_args['default_output']:
                inputs[subject] = os.path.join(DEFAULT_BIDS_FOLDER,
                                               os.path.basename(subject))

            # add all control files to 'data' folder
            for element in control_files:
                inputs[element] = os.path.join(DEFAULT_BIDS_FOLDER,
                                               os.path.basename(element))

            if not os.path.isdir(DEFAULT_RESULT_FOLDER):
                os.mkdir(DEFAULT_RESULT_FOLDER)
            inputs[extra_args['default_output']] = DEFAULT_RESULT_FOLDER

            # Define mount points
            docker_mount = " -v $PWD/{SUBJECT_DIR}:/bids:ro -v $PWD/{OUTPUT_DIR}:/output ".format(
                SUBJECT_DIR=DEFAULT_BIDS_FOLDER,
                OUTPUT_DIR=DEFAULT_RESULT_FOLDER)

            analysis = analysis_level
            outputs = [DEFAULT_RESULT_FOLDER]
        else:
            # Use local filesystem as reference
            # Define mount points
            docker_mount = " -v {SUBJECT_DIR}:/bids:ro -v {OUTPUT_DIR}:/output ".format(
                SUBJECT_DIR=subject,
                OUTPUT_DIR=extra_args['data_output_dir'])

            analysis = "{0} --participant_label {1}".format(analysis_level,
                                                            subject_name)

        if extra_args['freesurfer_license']:
            if extra_args['transfer_data']:
                inputs[freesurfer_license] = os.path.basename(extra_args['freesurfer_license'])
                freesurfer_path = "$PWD/{0}".format(inputs[freesurfer_license])
            else:
                freesurfer_path = extra_args['freesurfer_license']
            docker_mount += " -v {0}:/opt/freesurfer/license.txt ".format(freesurfer_path)

        arguments = DOCKER_RUN_COMMAND.format(DOCKER_MOUNT=docker_mount,
                                              DOCKER_TO_RUN=docker_run,
                                              ANALYSIS=analysis)

        gc3libs.log.debug("Creating application for executing: %s", arguments)

        Application.__init__(
            self,
            arguments=arguments,
            inputs=inputs,
            outputs=outputs,
            stdout='{0}.log'.format(subject_name),
            join=True,
            executables=executables,
            **extra_args)

    def terminated(self):
        """
        checks exitcode. If out-of-memory is somehow detected (e.g. exit code 137)
        try re-submit increasing memory allocation
        :return: None
        """
        if self.execution.returncode == 137:
            if self.requested_memory and self.requested_memory < MAX_MEMORY:
                self.requested_memory *= 4*GB
                self.execution.returncode = (0, 99)


class GbidsRetriableTask(RetryableTask):
    def __init__(self, subject, subject_name, control_files, docker_run,
                 freesurfer_license, **extra_args):
        return GbidsApplication(subject, subject_name, control_files,
                                docker_run, freesurfer_license, **extra_args)


class GbidsScript(SessionBasedScript):
    """
    The ``gbids`` command keeps a record of jobs (submitted, executed
    and pending) in a session file (set name with the ``-s`` option); at
    each invocation of the command, the status of all recorded jobs is
    updated, output from finished jobs is collected, and a summary table
    of all known jobs is printed.

    Options can specify a maximum number of jobs that should be in
    'SUBMITTED' or 'RUNNING' state; ``gbids`` will delay submission of
    newly-created jobs so that this limit is never exceeded.

    Once the processing of all chunked files has been completed, ``gbids``
    aggregates them into a single larger output file located in
    'self.params.output'.
    """

    def __init__(self):
        self.bids_app_execution = DEFAULT_DOCKER_BIDS_APP
        SessionBasedScript.__init__(
            self,
            version=__version__,
            application=GbidsApplication,
            stats_only_for=GbidsApplication,
        )

    def setup_args(self):
        self.add_param("bids_app", type=str,
                       help="Name of BIDS App to run. " 
                            " Images are listed at: http://bids-apps.neuroimaging.io/apps/ ")

        self.add_param("bids_input_folder", type=existing_directory,
                       help="Root location of input data. Note: expects folder in "
                            "BIDS format.")

        self.add_param("bids_output_folder", type=str, help="Location of the "
                                                            " results.")

        self.add_param("analysis_level", type=str,
                       help="analysis_level: participant: 1st level\n"
                            "group: second level. Bids-Apps specs allow for multiple substeps "
                            "(e.g., group1, group2."
                            "Allowed values: {0}.".format(ANALYSIS_LEVELS))

    def setup_options(self):
        self.add_param("-F", "--datatransfer", dest="transfer_data",
                       action="store_true", default=False,
                       help="Transfer input data to compute nodes. "
                            "If False, data will be assumed be already visible on "
                            "compute nodes - e.g. shared filesystem. "
                            "Default: %(default)s.")

        self.add_param("-L", "--license", metavar="[PATH]",
                       type=existing_file,
                       dest="freesurfer_license", default=None,
                       help="Location of freesurfer license file. Default: %(default)s.")

    def parse_args(self):
        """
        Check for valid analysis level.
        merge bids_app and related execution arguments
        """
        assert self.params.analysis_level in ANALYSIS_LEVELS, "Unknown analysis level {0}. " \
                                                              "Allowed values are {1}".format(self.params.analysis_level,
                                                                                              ANALYSIS_LEVELS)

        self.bids_app_execution = self.params.bids_app
        self.params.bids_output_folder = os.path.abspath(self.params.bids_output_folder)

    def new_tasks(self, extra):
        """
        if analysis type is 'group'
           create single gbidsApplication with all input data
        if analysis type is 'participants'
           for each valid input file create a new GbidsApplication
        """
        tasks = []
        control_files = _get_control_files(self.params.bids_input_folder)

        if self.params.transfer_data and not os.path.isdir(os.path.join(self.session.path,
                                                                        DEFAULT_RESULT_FOLDER)):
            os.mkdir(os.path.join(self.session.path,
                                  DEFAULT_RESULT_FOLDER))

        if _is_participant_analysis(self.params.analysis_level):
            # participant level analysis
            for (subject_dir, subject_name) in _get_subjects(self.params.bids_input_folder):
                job_name = subject_name

                if not self.params.transfer_data:
                    # Use root BIDS folder
                    subject_dir = self.params.bids_input_folder

                extra_args = extra.copy()
                extra_args['transfer_data'] = self.params.transfer_data
                extra_args['default_output'] = os.path.join(self.session.path,
                                                            DEFAULT_RESULT_FOLDER)
                extra_args['jobname'] = job_name
                extra_args['output_dir'] = os.path.join(os.path.abspath(self.params.bids_output_folder),
                                                        '.compute',
                                                        subject_name)
                extra_args['data_output_dir'] = os.path.join(os.path.abspath(self.params.bids_output_folder),
                                                             subject_name)

                extra_args['freesurfer_license'] = self.params.freesurfer_license

                self.log.debug("Creating Application for subject {0}".format(subject_name))

                tasks.append(GbidsApplication(
                    self.bids_app_execution,
                    subject_dir,
                    subject_name,
                    control_files,
                    self.params.analysis_level,
                    **extra_args))

        else:
            # Group level analysis
            subject_name = self.params.analysis_level
            extra_args = extra.copy()
            extra_args['jobname'] = self.params.analysis_level
            extra_args['data-transfer'] = self.params.transfer_data
            extra_args['output_dir'] = os.path.join(self.params.bids_output_folder,
                                                    '.compute')
            extra_args['data_output_dir'] = os.path.join(os.path.abspath(self.params.bids_output_folder),
                                                         subject_name)
            extra_args['freesurfer_license'] = self.params.freesurfer_license

            self.log.debug("Creating Application for analysis {0}".format(self.params.analysis_level))
            tasks.append(GbidsApplication(
                self.bids_app_execution,
                self.params.bids_input_folder,
                None,
                control_files,
                self.params.analysis_level,
                **extra_args))

        return tasks

    def after_main_loop(self):
        """
        Merge all results from all subjects into `results` folder
        """

        for task in self.session:
            if isinstance(task, GbidsApplication) and task.execution.returncode == 0:
                gc3libs.log.debug("Moving tasks {0} results from {1} to {2}".format(task.subject_name,
                                                                                    task.data_output_dir,
                                                                                    self.params.bids_output_folder))
                gc3libs.utils.movetree(task.data_output_dir, self.params.bids_output_folder)


# run script, but allow GC3Pie persistence module to access classes defined here;
# for details, see: http://code.google.com/p/gc3pie/issues/detail?id=95
if __name__ == "__main__":
    import gbids

    gbids.GbidsScript().run()
