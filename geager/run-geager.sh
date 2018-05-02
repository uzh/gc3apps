#!/usr/bin/env bash
#
# run_geager.sh -- wrapper script for executing Singularity container for EAGER
#
# Authors: Sergio Maffioletti <sergio.maffioletti@uzh.ch>
#
# Copyright (c) 2018, 2019 S3IT, University of Zurich, http://www.s3it.uzh.ch/
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

usage () {
    cat <<__EOF__
Usage:
  ${me} CONTAINER SUBJECT_FOLDER
__EOF__
}


echo "[`date`: Start]"

# Check input arguments
# the SCRIPT argument has to be present
if [ $# -lt 2 ]; then
    echo "Missing required argument(s)."
    usage
    exit 1
fi

# Fetch singularity container
container=$1
subject=$2

echo "Pulling $container... "
singularity pull ${container}

echo "Running... "
singularity exec -B ${subject}:/data $PWD/${container} eagercli /data
RET=$?

echo "[`date`: Stop with exit code: ${RET}]"

exit ${RET}
