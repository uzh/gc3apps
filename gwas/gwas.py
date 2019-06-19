#! /usr/bin/env python
#
#   gwas.py -- Front-end script for running R function
#   `gwas` over large number of chromosomes data.
#
#   Copyright (C) 2019, 2020 S3IT, University of Zurich
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
Front-end script for submitting multiple `R` jobs.
It uses the generic `gc3libs.cmdline.SessionBasedScript` framework.

See the output of ``gwas.py --help`` for program usage
instructions.
"""

# summary of user-visible changes
__changelog__ = """
  2019-02-08:
  * Initial version
"""
__author__ = 'Sergio Maffioletti <sergio.maffioletti@uzh.ch>'
__docformat__ = 'reStructuredText'
__version__ = '1.0'

# run script, but allow GC3Pie persistence module to access classes defined here;
# for details, see: http://code.google.com/p/gc3pie/issues/detail?id=95
if __name__ == "__main__":
    import gwas
    gwas.GwasScript().run()

import os
import sys
import gc3libs
from gc3libs import Application
from gc3libs.cmdline import SessionBasedScript, existing_file, existing_directory

DOCKER_CMD = "docker run -v {DATA_MOUNT}:/data {CHROMOSOMES_MOUNT}:/chromosomes -v {OUTPUT_MOUNT}:/output smaffiol/gwas:{was_release} /data /chromosomes /output"
DEFAULT_WAS_RELEASE = "1.0.0"
DEFAULT_REMOTE_OUTPUT_FILE = "./output"

## custom application class
class GwasApplication(Application):
    """
    Custom class to wrap the execution of the Matlab function
    over a subset of the total number of events.
    """
    application_name = 'gwas'
    
    def __init__(self, input_folder, chromosomes_folder, **extra_args):

        executables = []
        inputs = dict()
        outputs = dict()

        # Set output
        outputs[DEFAULT_REMOTE_OUTPUT_FILE] = DEFAULT_REMOTE_OUTPUT_FILE

        # Note: input data are amde available through network fileshare
        # inputs[data_folder] = os.path.basename(input_folder)
        # inputs[chromosomes_folder] = os.path.basename(chromosomes_folder)
            
        arguments = DOCKER_CMD.format(DATA_MOUNT=input_folder,
                                      CHROMOSOMES_MOUNT=chromosomes_folder,
                                      OUTPUT_MOUNT=outputs[DEFAULT_REMOTE_OUTPUT_FILE],
                                      was_release = extra_args["was_release"])

        gc3libs.log.debug("Creating application for executing: %s",
                          arguments)
        
        Application.__init__(
            self,
            arguments = arguments,
            inputs = inputs,
            outputs = outputs,
            stdout = 'log',
            join=True,
            executables = executables,
            **extra_args)


class GwasScript(SessionBasedScript):
    """
    Take total number of events and create a list of chunked events.
    For each chunk, run the provided Matlab function.

    The ``gwas`` command keeps a record of jobs (submitted, executed
    and pending) in a session file (set name with the ``-s`` option); at
    each invocation of the command, the status of all recorded jobs is
    updated, output from finished jobs is collected, and a summary table
    of all known jobs is printed.
    
    Options can specify a maximum number of jobs that should be in
    'SUBMITTED' or 'RUNNING' state; ``gwas`` will delay submission of
    newly-created jobs so that this limit is never exceeded.

    Once the processing of all chunked files has been completed, ``gwas``
    aggregates them into a single larger output file located in 
    'self.params.output'.
    """

    def __init__(self):
        SessionBasedScript.__init__(
            self,
            version = __version__, # module version == script version
            application = GwasApplication, 
            # only display stats for the top-level policy objects
            # (which correspond to the processed files) omit counting
            # actual applications because their number varies over
            # time as checkpointing and re-submission takes place.
            stats_only_for = GwasApplication,
            )

    def setup_args(self):
        
        self.add_param("input", type=existing_directory,
                       help="Location of input data.")

        self.add_param('chromosomes', type=existing_directory,
                       help="Location of chromosomes files.")

    def setup_options(self):
        self.add_param("-R", "--release", dest="was_release",
                       default=DEFAULT_WAS_RELEASE,
                       help="Use version of was docker image. " \
                            "Default: %(default)s.")

    def new_tasks(self, extra):
        """
        Read content of 'command_file'
        For each command line, generate a new Application
        """
        tasks = []

        for input_folder in os.listdir(self.params.input):
            extra_args = extra.copy()
            extra_args["jobname"] = input_folder
            extra_args["docker_was_version"] = self.params.was_release
            
            tasks.append(GwasApplication(
                os.path.abspath(os.path.join(self.params.input, input_folder)),
                os.path.abspath(self.params.chromosomes),
                **extra_args))
                    
        return tasks
