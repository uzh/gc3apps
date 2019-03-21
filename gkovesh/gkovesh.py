#! /usr/bin/env python
#
#   gkovesh.py -- Front-end script for running Docker KOVESH apps
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
Front-end script for submitting multiple `KOVESH apps` jobs fetching
docker images from the `KOVESH apps` repository.

It uses the generic `gc3libs.cmdline.SessionBasedScript` framework.

See the output of ``gkovesh.py --help`` for program usage
instructions.

Example of docker execution:
docker run -i --rm -v /mnt/filo/data/ds005:/kovesh_dataset:ro kovesh/fmriprep /kovesh_dataset /outputs participant --participant_label 01

gkovesh takes KOVESH files as input.
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
import tempfile

# GC3Pie specific libraries
import gc3libs
import gc3libs.exceptions
from gc3libs import Application
from gc3libs.workflow import RetryableTask
from gc3libs.cmdline import SessionBasedScript, existing_file, existing_directory, positive_int
import gc3libs.utils
from gc3libs.quantity import GB
from gc3libs.utils import write_contents

# Defaults
RUN_DOCKER = "./run_docker.sh"
MAX_MEMORY = 32*GB
DEFAULT_KOVESH_FOLDER = "$PWD/data/"
DEFAULT_RESULT_FOLDER_LOCAL = "output"
DEFAULT_RESULT_FOLDER_REMOTE = "$PWD/output/"
DEFAULT_DOCKER_KOVESH_ARGS = "--no-submm-recon"
DEFAULT_FREESURFER_LICENSE_FILE = "license.txt"
DEFAULT_DOCKER_KOVESH_APP = "poldracklab/fmriprep " + DEFAULT_DOCKER_KOVESH_ARGS
ANALYSIS_LEVELS = ["participant", "group1", "group2", "group"]
DOCKER_RUN_COMMAND = "sudo docker run -i --rm {DOCKER_MOUNT} {DOCKER_TO_RUN} /kovesh /output {ANALYSIS} "
COPY_COMMAND = "cp {0}/* {1} -Rf"
RUN_DOCKER_SCRIPT="""#!/bin/bash

echo "[`date`]: Start processing for subject {subject}"
group=`id -g -n`
sudo docker run -i --rm -v {data}:/kovesh -v {output}:/output {container} /kovesh /output {analysis} --participant_label {subject}
RET=$?
echo "fixing local filesystem permission"
sudo chown -R $USER:$group {output}
echo "[`date`]: Done with code $RET"
exit $RET
"""


# Utility methods


# Custom application class


class GkoveshApplication(Application):
    """
    Custom class to wrap the execution of the R scripts passed in src_dir.
    """
    application_name = 'gkovesh'

    def __init__(self, file_list, **extra_args):

        executables = []
        inputs = dict()
        outputs = []

        Application.__init__(
            self,
            arguments="hostname",
            inputs=inputs,
            outputs=outputs,
            stdout='log',
            join=True,
            executables=executables,
            **extra_args)

class GkoveshScript(SessionBasedScript):
    """
    The ``gkovesh`` command keeps a record of jobs (submitted, executed
    and pending) in a session file (set name with the ``-s`` option); at
    each invocation of the command, the status of all recorded jobs is
    updated, output from finished jobs is collected, and a summary table
    of all known jobs is printed.

    Options can specify a maximum number of jobs that should be in
    'SUBMITTED' or 'RUNNING' state; ``gkovesh`` will delay submission of
    newly-created jobs so that this limit is never exceeded.

    Once the processing of all chunked files has been completed, ``gkovesh``
    aggregates them into a single larger output file located in
    'self.params.output'.
    """

    def __init__(self):
        self.kovesh_app_execution = DEFAULT_DOCKER_KOVESH_APP
        SessionBasedScript.__init__(
            self,
            version=__version__,
            application=GkoveshApplication,
            stats_only_for=GkoveshApplication,
        )

    def setup_args(self):
        self.add_param("input_folder", type=existing_directory,
                       help="Input data")

    def setup_options(self):
        self.add_param("-K", "--chunk", dest="chunk",
                       type=positive_int,
                       default=1073741824,
                       help="Group data by size. Chunk expressed in bytes. "\
                       "Default: %(default)s.")

    def new_tasks(self, extra):
        """
        if analysis type is 'group'
           create single gkoveshApplication with all input data
        if analysis type is 'participants'
           for each valid input file create a new GkoveshApplication
        """
        tasks = []

        filelist = []
        total_size = 0

        for data in os.listdir(self.params.input_folder):
            data = os.path.join(self.params.input_folder, data)
            if (total_size + os.path.getsize(data)) <= self.params.chunk:
                filelist.append(data)
                total_size += os.path.getsize(data)
            else:
                extra_args = extra.copy()
                extra_args['jobname'] = "mbe"

                self.log.debug("Creating Application for subject {0}".format(extra_args['jobname']))

                tasks.append(GkoveshApplication(filelist, **extra_args))

                filelist = []
                total_size = 0

        if len(filelist) > 0:
                extra_args = extra.copy()
                extra_args['jobname'] = "mbe"

                self.log.debug("Creating Application for last subject {0}".format(extra_args['jobname']))

                tasks.append(GkoveshApplication(filelist, **extra_args))
            
        return tasks

# run script, but allow GC3Pie persistence module to access classes defined here;
# for details, see: http://code.google.com/p/gc3pie/issues/detail?id=95
if __name__ == "__main__":
    import gkovesh

    gkovesh.GkoveshScript().run()
