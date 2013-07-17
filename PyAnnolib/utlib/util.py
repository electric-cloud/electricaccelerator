# Copyright (c) 2012 by Cisco Systems, Inc.

import subprocess
import os
import select
import sys

# The utlib directory, where this file (util.py) is located
this_dir = os.path.abspath(os.path.dirname(__file__))

# The top of the distro, where 'unittest' script is located.
DISTRO_DIR = os.path.dirname(this_dir)

# The location for extra files needed for the unit-test
UTFILES_DIR = os.path.join(DISTRO_DIR, "utfiles")

SUCCESS = 0
def exec_cmdv(cmdv, cwd=None, stdin=None):
    """Run the commands in cmdv, returning (retval, output),
    where output is stdout and stderr combined.
    If cwd is given, the child process runs in that directory.
    If a filehandle is passed as stdin, it is used as stdin."""

    try:
        output = subprocess.check_output(cmdv, stderr=subprocess.STDOUT,
                cwd=cwd, stdin=stdin)
        retval = SUCCESS

    # If file isn't executable
    except OSError, e:
        output = str(e)
        retval = None

    # If process returns non-zero
    except subprocess.CalledProcessError, e:
        output = e.output
        retval = e.returncode

    return (retval, output)


def exec2_cmdv(cmdv, cwd=None):
    """Run the commands in argv, returning (retval, stdout, stderr)"""

    # This is the size of pipe buffers in Linux.
    # It's safe to use any size here, but by matching the
    # maxmium pipe buffer size, our operations will be more efficient.
    KB = 1024
    BUFSIZE = 64 * KB

    # Used in error messages
    ERROR_PREFIX = "unittest"

    # The 2 output buffers
    stdout = ""
    stderr = ""

    # Run the command in a child process, setting up the file descriptors
    # (pipes) for communication.
    try:
        child = subprocess.Popen(cmdv,  # The command to run
                cwd=cwd,                # Set CWD
                bufsize=0,              # No buffering
                stdin=None,             # Inherit the parent's stdin
                stdout=subprocess.PIPE, # Create a new pipe for stdout
                stderr=subprocess.PIPE) # Create a new pipe for stderr

    # If file isn't executable
    except OSError, e:
        error_string = str(e)
        return (None, "", error_string)

    # These are the file descriptors where we will expect to read data.
    # That is, we are reading what the child process is writing.
    fd_r = [child.stdout, child.stderr]

    # This loop runs, continuously reading data from child.stdout
    # and child.stderr, until both those pipes are closed (when we
    # detect EOF on those pipes)
    while 1:
        # When both pipes are closed (no more file descriptors to wait upon),
        # stop this loop.
        if len(fd_r) == 0:
            break

        # Ask the OS to tell us if any file descriptor is ready for action.
        try:
            (iready, oready, eready) = select.select(fd_r, [], [])

        except select.error, err:
            # Check the error code
            (err_errno, err_text) = err
            print >> sys.stderr, "exec2_cmdv select() error:", err_errno, err_text
            return (None, None, None)
            sys.exit(1)

        # We only asked select() to wait on the readable file
        # descriptors. Check that here.
        if (not iready) or oready or eready:
            sys.exit("%s: unexpected select() termination: %s, %s, %s" % \
                    (ERROR_PREFIX, iready, oready, eready))

        # Loop across oready, as perhaps both stdout & stderr have
        # data at the same time.
        for fd in iready:

            # Read a chunk of data from the pipe. Use os.read()
            # instead of fd.read() because I have seen Python call
            # the read() syscall twice with one fd.read() call. This
            # can block, of course.
            data = os.read(fd.fileno(), BUFSIZE)

            # 0-length means EOF was reached on the pipe,
            # so remove it from the list of writable fd's
            if len(data) == 0:
                fd_r.remove(fd)
                continue

            # 'tee' the data to our stdout or stderr, as appropriate, and log
            if fd == child.stdout:
                # Append the data
                stdout += data

            elif fd == child.stderr:
                # Append the data
                stderr += data

            else:
                sys.exit("%s: unexpected file descriptor %s" % (ERROR_PREFIX, fd))
    # The select() loop is over.
    # Wait as the child process terminates
    rc = child.wait()

    try:
        child.stdout.close()
        child.stderr.close()
    except IOError:
        pass
    
    # And pass on the return code
    return (rc, stdout, stderr)


