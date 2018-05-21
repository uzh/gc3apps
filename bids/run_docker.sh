#!/bin/bash
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

# utility functions
me=$(basename "$0")

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
  $me [options] DOCKER_TO_RUN BIDS_INPUT OUTPUT_FOLDER ANALYSIS_TYPE SUBJECT_LABEL

Run BIDS/App docker containe 'DOCKER_TO_RUN'

Options:
  -d            Enable verbose logging
  -h            Print this help text

__EOF__
}

## parse command-line

short_opts='dh'
long_opts='debug,help'

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
        --debug|-d)    set -x ;;
        --help|-h)     usage; exit 0 ;;
        --)            shift; break ;;
    esac
    shift
done

## sanity checks

# the SCRIPT argument has to be present
if [ $# -lt 5 ]; then
    die 1 "Missing required arguments. Type '$me --help' to get usage help."
fi

## main
echo "[`date`]: Start"

DOCKER_TO_RUN="$1"
DOCKER_DATA="$2"
DOCKER_OUTPUT="$3"
ANALYSIS="$4"
SUBJECT="$5"

echo "running: sudo docker run -i --rm -v $DOCKER_DATA:/bids -v $DOCKER_OUTPUT:/output $DOCKER_TO_RUN /bids /output $ANALYSIS --participant_label $SUBJECT"
# sudo docker run -i --rm -v $DOCKER_DATA:/bids -v $DOCKER_OUTPUT:/output $DOCKER_TO_RUN /bids /output $ANALYSIS --participant_label $SUBJECT
RET=$?
# Fix local filesystem permission
echo "fixing local filesystem permission"
# chown -R $UID:$GID $DOCKER_OUTPUT

echo "[`date`]: Done with code $RET"
exit $RET
