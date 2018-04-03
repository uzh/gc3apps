#! /usr/bin/env python
#
#   gstacks.py -- Front-end script for submitting multiple jobs running
#   stacks in docker/singularity containers
#
#   Copyright (c) 2018 2019 S3IT, University of Zurich, http://www.s3it.uzh.ch/
#
#   This program is free software: you can redistribute it and/or modify
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
Front-end script for submitting multiple `stacks` jobs.
It uses the generic `gc3libs.cmdline.SessionBasedScript` framework.

See the output of ``gstacks --help`` for program usage instructions.
"""

# summary of user-visible changes
__changelog__ = """

  2014-04-16:
  * Retrieve only specific result folder as output.
  * Initial experimental support for S3 repository

  2014-02-24:
  * Initial release, forked off the ``ggeosphere`` sources.
"""
__author__ = 'Sergio Maffioletti <sergio.maffioletti@gc3.uzh.ch>'
__docformat__ = 'reStructuredText'
__version__ = "1.0a"

import os

# gc3 library imports
from gc3libs import Application
from gc3libs.cmdline import SessionBasedScript, existing_file

# Default values
DEFAULT_INPUT_FOLDER = "data/"
DEFAULT_RESULT_FOLDER = "output"
DEFAULT_DOCKER_IMAGE = "smaffiol/stacks:2.0Beta9a"
DEFAULT_STACKS_RUN_SCRIPT = "./gc3pie-run-stacks.sh"
DOCKER_MOUNT = " -v $PWD/input:/input -v $PWD/{0}:/{0} ".format(DEFAULT_RESULT_FOLDER)
DOCKER_RUN_COMMAND = "sudo docker run -i --rm {DOCKER_MOUNT} --entrypoint {STACKS_RUN_SCRIPT} {DOCKER_TO_RUN} "


# utility functions
def get_valid_input_pair(input_folder):
    """
    scans input folder [non recursively]
    for each valid compressed fastq file [fastq.gz]
    search for a pair of type [R1,R2].
    Search is done at filename level.
    """
    r1list = [infile.split('R1')[0] for infile in os.listdir(input_folder)
              if infile.endswith('R1.fastq.gz')]

    input_list = [(os.path.join(input_folder,
                                "{0}R1.fastq.gz".format(infile.split('R2')[0])),
                   os.path.join(input_folder,
                                "{0}R2.fastq.gz".format(infile.split('R2')[0]))) for infile in os.listdir(input_folder)
                  if infile.endswith('R2.fastq.gz') and infile.split('R2')[0] in r1list]

    return input_list


# custom application class

class GstacksApplication(Application):
    """
    Fetches execution wrapper, input file and checks
    whether optional arguments have been passed.
    Namely ''wclust'' that sets the stacks clustering
    threshold and ''paramsfile'' needed to run stacks.
    """

    application_name = 'gstacks'

    def __init__(self, input_files, **extra_args):
        """
        The wrapper script is being used for start the simulation.
        """

        inputs = []

        inputs[extra_args['stack_exec']] = DEFAULT_STACKS_RUN_SCRIPT
        for f in input_files:
            inputs[f] = "./input/{0}".format(os.path.basename(f))

        inputs[extra_args["decoy_output_folder"]] = DEFAULT_RESULT_FOLDER

        docker_mount = "-v $PWD/input:/input -v $PWD/output:/output "

        # Add memory requirement
        # extra_args.setdefault('requested_memory', 1.5*GiB)

        Application.__init__(
            self,
            arguments=DOCKER_RUN_COMMAND.format(DOCKER_MOUNT=docker_mount,
                                                STACKS_RUN_SCRIPT=DEFAULT_STACKS_RUN_SCRIPT,
                                                DOCKER_TO_RUN=extra_args["docker"]),
            inputs=inputs,
            outputs=DEFAULT_RESULT_FOLDER,
            stdout='gstacks.log',
            join=True,
            **extra_args)


# main script class

class GstacksScript(SessionBasedScript):
    """
Scan the specified INPUT directories recursively for simulation
directories and submit a job for each one found; job progress is
monitored and, when a job is done, its output files are retrieved back
into the simulation directory itself.

The ``gstacks`` command keeps a record of jobs (submitted, executed
and pending) in a session file (set name with the ``-s`` option); at
each invocation of the command, the status of all recorded jobs is
updated, output from finished jobs is collected, and a summary table
of all known jobs is printed.  New jobs are added to the session if
new input files are added to the command line.

Options can specify a maximum number of jobs that should be in
'SUBMITTED' or 'RUNNING' state; ``gstacks`` will delay submission of
newly-created jobs so that this limit is never exceeded.
    """

    def __init__(self):
        SessionBasedScript.__init__(
            self,
            version=__version__,
            application=GstacksApplication,
            stats_only_for=GstacksApplication,
        )

    def setup_options(self):
        self.add_param("-E", "--stack-run-script",
                       metavar="PATH",
                       type=existing_file,
                       dest="stacks_exec",
                       default=DEFAULT_STACKS_RUN_SCRIPT,
                       help="Alternative stacks execution script."
                            "Default: %(default)s.")

        self.add_param("-D", "--docker", metavar="[PATH]",
                       dest="docker", default=DEFAULT_DOCKER_IMAGE,
                       help="Stacks docker image. Default: '%(default)s'.")

    def setup_args(self):

        self.add_param('input_container', type=str,
                       help="Path to local folder containing fastq files.")

    def new_tasks(self, extra):

        tasks = []

        # Create decoy output folder
        if not os.path.isdir(os.path.join(self.session.name, "output")):
            os.makedirs(os.path.join(self.session.name, "output"))

        for input_files in get_valid_input_pair(self.params.input_folder):
            # extract job name from the 1st file of the input_file pair
            job_name = "%s" % os.path.basename(input_files[0]).split(".fastq.gz")[0]

            extra_args = extra.copy()
            extra_args['jobname'] = job_name

            # FIXME: ignore SessionBasedScript feature of customizing
            # output folder
            extra_args['output_dir'] = self.params.output
            extra_args['output_dir'] = extra_args['output_dir'].replace('NAME', job_name)
            extra_args['output_dir'] = extra_args['output_dir'].replace('SESSION', job_name)
            extra_args['output_dir'] = extra_args['output_dir'].replace('DATE', job_name)
            extra_args['output_dir'] = extra_args['output_dir'].replace('TIME', job_name)

            extra_args["docker"] = self.params.docker
            extra_args["decoy_output_folder"] = os.path.join(self.session.name, "output")

            self.log.info("Creating Task for input file: %s" % input_files)

            tasks.append(GstacksApplication(
                input_files,
                **extra_args
            ))

            return tasks


# run script, but allow GC3Pie persistence module to access classes defined here;
# for details, see: https://github.com/uzh/gc3pie/issues/95
if __name__ == "__main__":
    import gstacks
    gstacks.GstacksScript().run()
