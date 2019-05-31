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
whereami = os.path.dirname(os.path.abspath(__file__))
KOVESCH_RUN="python3 MC_script_gt.py -i {input_csv} -n {repetitions} -o {output}"
KOVESCH_BASH=os.path.join(whereami,"./run_kovesh.sh")

# Utility methods

def _make_temp_run_docker_file(location, input_csv, seed):
    """
    Create execution script to control docker execution and post-process
    """
    try:
        (fd, tmp_filename) = tempfile.mkstemp(prefix="sbj{0}-".format(subject),dir=location)
        write_contents(tmp_filename, RUN_SCRIPT.format(data=data,
                                                       output=output,
                                                       container=docker,
                                                       analysis=analysis,
                                                       subject=subject))
        os.chmod(tmp_filename, 0755)
        return tmp_filename
    except Exception, ex:
        gc3libs.log.debug("Error creating execution script."
                          "Error type: %s. Message: %s" % (type(ex), ex.message))
        raise

def _get_data_group_size(location):
    """
    Return max file size in `location`
    """

    return max([os.path.getsize(os.path.join(location,data_size)) for data_size in os.listdir(location) if os.path.isfile(data_size)])


# Custom application class


class GkoveshApplication(Application):
    """
    Custom class to wrap the execution of the R scripts passed in src_dir.
    """
    application_name = 'gkovesh'

    def __init__(self, file_list, motif_notation, repetitions, **extra_args):

        executables = []
        inputs = dict()
        outputs = []

        for data in file_list:
            inputs[data] = "./data/{0}".format(os.path.basename(data))

        inputs[KOVESCH_BASH] = "./run.sh"
        inputs[motif_notation] = "./data/{0}".format(os.path.basename(motif_notation))
        # outputs = "./output"
        arguments = "{0} ./data ./output {1}".format(inputs[KOVESCH_BASH],
                                                     repetitions)

        Application.__init__(
            self,
            arguments=arguments,
            inputs=inputs,
            outputs=gc3libs.ANY_OUTPUT,
            stdout='log',
            join=True,
            executables=[inputs[KOVESCH_BASH]],
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
        SessionBasedScript.__init__(
            self,
            version=__version__,
            application=GkoveshApplication,
            stats_only_for=GkoveshApplication,
        )

    def setup_args(self):
        self.add_param("input_folder", type=existing_directory,
                       help="Input data")

        self.add_param("motif_notation", type=existing_file,
                       help="Motif Notation file")

    def setup_options(self):
        self.add_param("-K", "--chunk", dest="chunk",
                       type=positive_int,
                       default=1073741824,
                       help="Group data by size. Chunk expressed in bytes. "\
                       "Default: %(default)s.")

        self.add_param("-z", "--seed", dest="seed",
                       type=positive_int,
                       default=67,
                       help="Random seed (needed for network randomization). "\
                       "Default: %(default)s.")

        self.add_param("-r", "--repetitions", dest="repetitions",
                       type=positive_int,
                       default=1,
                       help="Number of randomizations to perform. "\
                       "Default: %(default)s.")
                                       

        self.add_param("-g", "--group_repetitions", dest="groups",
                       type=positive_int,
                       default=1,
                       help="Run repetitions together in groups. "\
                       "Default: %(default)s.")


    def parse_args(self):
        self.group_repetitions = int(self.params.repetitions / self.params.groups)
        assert self.group_repetitions > 0, "repetitions sould be higher than groups"

        self.data_group_size = max(self.params.chunk,
                                   _get_data_group_size(self.params.input_folder))
        self.log.info("Setting data group size to {0}bytes".format(self.data_group_size))

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
            if (total_size + os.path.getsize(data)) <= self.data_group_size:
                filelist.append(data)
                total_size += os.path.getsize(data)
            else:
                extra_args = extra.copy()
                extra_args['jobname'] = os.path.basename(filelist[0])

                self.log.debug("Creating Application for subject {0}".format(extra_args['jobname']))

                for rep_indx in range(0, self.group_repetitions):
                    tasks.append(GkoveshApplication(filelist,
                                                    self.params.motif_notation,
                                                    self.params.groups,
                                                    **extra_args))

                filelist = []
                total_size = 0

        if len(filelist) > 0:
                extra_args = extra.copy()
                extra_args['jobname'] = os.path.basename(filelist[0])

                self.log.debug("Creating Application for last subject {0}".format(extra_args['jobname']))

                for rep_indx in range(0, self.group_repetitions):
                    tasks.append(GkoveshApplication(filelist,
                                                    self.params.motif_notation,
                                                    self.params.repetitions,
                                                    **extra_args))

        return tasks

# run script, but allow GC3Pie persistence module to access classes defined here;
# for details, see: http://code.google.com/p/gc3pie/issues/detail?id=95
if __name__ == "__main__":
    import gkovesh

    gkovesh.GkoveshScript().run()
