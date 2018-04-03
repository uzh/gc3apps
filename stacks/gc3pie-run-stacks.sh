#!/bin/bash

echo "[`date`: Start]"

echo "Step 1: process_radtags"
time process_radtags -p /input -o /output -e apeKI -r -c -q
RET=$?
echo "Step 1 terminated with exit code: $RET"

echo "Step 2: ustacks"
ustack_out=/output/ustacks
mkdir $ustack_out

# Get R1 filename
ustacks_input=`ls /output/*R1*`
time ustacks -f $ustacks_input -o $ustack_out -M 4 -p -1 -i 9
RET=$?
echo "Step 2 terminated with exit code: $RET"

echo "[`date`: Stop]"
