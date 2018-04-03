===============
gstacks README
===============

Requirements for running ``gstacks``
------------------------------------

``gc3pie_`` needs to be installed.

gstacks takes an input folder containing 2 or more .fastq.gz files (Note: fastq files are assumed to be in pairs).
For each found pair, ``gstacks`` runs the stacks protocol_ and collects its results.

The ``gstacks`` command keeps a record of jobs (submitted,
executed and pending) in a session file (set name with the ``-s``
option); at each invocation of the command, the status of all recorded
jobs is updated, output from finished jobs is collected, and a summary
table of all known jobs is printed.
 
Running ``gstacks``
-------------------

Step 1 (optional): Activate ScienceCloud API authentication
    If you are running on the University of Zurich ScienceCloud_, you need
    first to authenticate.
    Example: 
    $ source ~/gc3pie/bin/sc-authenticate.sh

    Provide UZH Webpass shortname and password at prompt as requested.

Step 2: Execute gstacks in `screen` mode
    usage: gstacks [OPTIONS] input_folder
    
    positional arguments:
        input_folder    Path to input folder containing valid input .fastq.gz
                        files.
    Example:
        $ screen -L `which gstacks` /data/fastqs/ -s today -o results -N -C 60

    *Note*: the `-N` option removes all previous executions. Use it **only**
    when you need to start a new simulation and forget about previous
    ones.

    Get a full list of ``gstacks`` option by:
    $ gstacks -h


Step 3: Detach from running `screen` session 
    Once ``gstacks`` runs (and it has been launched with the `-C`
    option, it will continuously supervise the execution of all provided
    input parameters until completion. In order to properly detach from
    the running session and let the ``gstacks`` run in background, it
    is necessary to detach from the running `screen` session.

    How to detach form a running `screen` session:
    $ Ctrl-A Ctrl-D

Step 4: periodically check the progress of the ``gstacks`` execution
    Either re-attach to the running `screen` session by:
    $ screen -r

    *Note*: remember to detach from the running screen session using the:
    ``$ Ctrl-A Ctrl-D`` command

    ...or check the content of the `screen` log file:
    $ less screen.log

Control a running ``gstacks`` session
---------------------------------------

Inspect status of the execution:
    $ gsession list <path to session folder>
    
    In case of nested workflows:
    $ gsession list -r <path to session folder>
    
    *Note*: ``-r`` show all jobs contained in a task collection, 
    not only top-level jobs.

Abort a running session:
    $ gsession abort <path to session folder>

Log session execution:
    * gsession log  <path to session folder>
    
    *Note*: increase log verbosity using ``-v`` option

.. _gc3pie: http://gc3pie.readthedocs.io/
.. _protocol: http://doi.org/10.1038/nprot.2017.123