#!/bin/bash

echo "[`date`: Start]"

cores=$( grep -c ^processor /proc/cpuinfo )

pairs=$( ls /input/*.fastq.gz )
echo "Step 1: process_radtags"
time process_radtags  $( echo $( ls /input/*.fastq.gz ) | awk '{print "-1 "$1 " -2 "$2}' ) -o /output -e apeKI -r -c -q
RET=$?
echo "Step 1 terminated with exit code: $RET"

echo "Step 2: ustacks"
ustack_out=/output/ustacks
mkdir $ustack_out

# Get R1 filename
ustacks_input=`ls /output/*R1.fq.gz`
time ustacks -f $ustacks_input -o $ustack_out -M 4 -p $cores -i 9
RET=$?
echo "Step 2 terminated with exit code: $RET"

echo "[`date`: Stop]"
