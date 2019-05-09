#!/bin/bash
#
# run_kovesh.sh -- wrapper script for executing KOVESH code
#
# Authors: Riccardo Murri <riccardo.murri@uzh.ch>,
#          Sergio Maffioletti <sergio.maffioletti@uzh.ch>
#
#   Copyright (c) 2019,2020 S3IT, University of Zurich,
#   http://www.s3it.uzh.ch/
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
me=$(basename "$0")

## defaults
docker_image="s3ituzh/count-motif:1.0.12"
## Exit status codes (mostly following <sysexits.h>)

# successful exit
EX_OK=0

# wrong command-line invocation
EX_USAGE=64

# missing dependencies (e.g., no C compiler)
EX_UNAVAILABLE=69

# wrong KOVESH version
EX_SOFTWARE=70

# cannot create directory or file
EX_CANTCREAT=73

# user aborted operations
EX_TEMPFAIL=75

# misused as: unexpected error in some script we call
EX_PROTOCOL=76


## helper functions

function die () {
    rc="$1"
    shift
    (echo -n "$me: ERROR: ";
        if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
    exit $rc
}


## usage info

usage () {
    cat <<__EOF__
Usage:
  $me [options] MAIN [ARGS]

Run KOVESH passing ARGS (if any) as command-line arguments.

Options:
  -v            Enable verbose logging
  -d		Docker image to use
  -h		Print this help

__EOF__
}

warn () {
  (echo -n "$me: WARNING: ";
      if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
}

have_command () {
  type "$1" >/dev/null 2>/dev/null
}

require_command () {
  if ! have_command "$1"; then
    die $EX_UNAVAILABLE "Could not find required command '$1' in system PATH. Aborting."
  fi
}

is_absolute_path () {
    expr match "$1" '/' >/dev/null 2>/dev/null
}


## parse command-line

short_opts='vd:h'
long_opts='verbose,docker,help'

# test which `getopt` version is available:
# - GNU `getopt` will generate no output and exit with status 4
# - POSIX `getopt` will output `--` and exit with status 0
getopt -T > /dev/null
rc=$?
if [ "$rc" -eq 4 ]; then
    # GNU getopt
    args=$(getopt --name "$me" --shell sh -l "$long_opts" -o "$short_opts" -- "$@")
    if [ $? -ne 0 ]; then
        die 1 "Type '$me --help' to get usage information."
    fi
    # use 'eval' to remove getopt quoting
    eval set -- $args
else
    # old-style getopt, use compatibility syntax
    args=$(getopt "$short_opts" "$@")
    if [ $? -ne 0 ]; then
        die 1 "Type '$me --help' to get usage information."
    fi
    set -- $args
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --verbose|-v)  verbose='-v' ;;
        --help|-h)     usage; exit 0 ;;
	--docker|-d)   docker_image=$2; shift ;;
        --)            shift; break ;;
    esac
    shift
done


## sanity checks

# the MAIN argument has to be present
if [ $# -lt 3 ]; then
    die 1 "Missing required argument(s). Type '$me --help' to get usage help."
fi

## main
echo "=== Starting at `date '+%Y-%m-%d %H:%M:%S'`"

datadir=`realpath ${1}`
outputprefix=`realpath ${2}`
repetitions="${3}"

for data in `ls $datadir`; do
    output_suffix=`basename $data`
    output="${outputprefix}/${output_suffix}"
    mkdir -p ${output}
    echo "running ${repetitions} runs for ${output_suffix}"
    sudo docker run -v ${datadir}:/data -v ${output}:/output ${docker_image} -i /data/${data} -n ${repetitions} -o /output -m /data/3Motif_notation.tsv
done

## All done.
echo "=== Script '${me}' done at `date '+%Y-%m-%d %H:%M:%S'`."

