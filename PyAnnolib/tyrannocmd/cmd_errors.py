# Copyright (c) 2014 by Cisco Systems, Inc.

import os
import sys
from pyannolib import annolib
import datetime

TYPE_JOB = 0
TYPE_MAKE = 1

def SubParser(subparsers):

    help = "Produce a nice error report"

    parser = subparsers.add_parser("errors", help=help)
    parser.set_defaults(func=Run)

    parser.add_argument("-o", metavar="FILE",
            help="Store output in FILE (stdout is default)")

    parser.add_argument("--tee", action="store_true",
            help="In addition to writing to -o FILE, tee to stdout")

    parser.add_argument("--exit-with-build-rc",
            action="store_true",
            help="Tyranno will exit with the build's return code")

    parser.add_argument("anno_file")

def find_error_jobs(build):
    """Returns all the Jobs that were not successful."""

    job_errors = []
    make_errors = []
    end_job = None

    for job in build.iterJobs():
        if job.getType() == annolib.JOB_TYPE_END:
            end_job = job
            continue

        if job.getType() != annolib.JOB_TYPE_RULE and \
                job.getType() != annolib.JOB_TYPE_PARSE and \
                job.getType() != annolib.JOB_TYPE_CONTINUATION:
            continue

        if job.getRetval() == job.SUCCESS:
            continue

        if job.getOutputs():
            # These can be parse jobs, or not
            make_errors.append(job)
        else:
            job_errors.append(job)

    return job_errors, make_errors, end_job

def report_make_chain(out_fh, chain):
    for make_proc in chain:
        print >> out_fh, "%s make[%s], CWD=%s" % (make_proc.getID(),
                make_proc.getLevel(), make_proc.getCWD())
        print >> out_fh, make_proc.getCmd()
        print >> out_fh

def print_error_job(out_fh, n, show_summary, build, job, report_type):

    make_proc = job.getMakeProcess()

    build_start_dt = build.getStartDateTime()

    if show_summary:
        if report_type == TYPE_JOB:
            print >> out_fh, "Failed Command #%d: %s" % (n, job.getName())
        else:
            print >> out_fh, "Failed Make #%d" % (n,)
        print >> out_fh

    print >> out_fh
    print >> out_fh, "Job ID: %s , Exit Value %s" % (job.getID(), job.getRetval())
    print >> out_fh, "CWD: %s" % (make_proc.getCWD(),)

    for timing in job.getTimings():

        if build_start_dt:
            job_start = float(timing.getInvoked())
            job_end = float(timing.getCompleted())
            job_start_dt = build_start_dt + \
                    datetime.timedelta(seconds=job_start)
            job_end_dt = build_start_dt + \
                    datetime.timedelta(seconds=job_end)
        else:
            job_start_dt = ""
            job_end_dt = ""

        print >> out_fh, "Node: %s  Start: %s (%s)" % (timing.getNode(),
                job_start_dt, timing.getInvoked())
        print >> out_fh, "      %s  End:   %s (%s)" % \
                (" " * len(timing.getNode()),
                job_end_dt, timing.getCompleted())
    print >> out_fh

    for cmd in job.getCommands():
        print >> out_fh, "Command:\n"
        argv = cmd.getArgv()
        print >> out_fh, argv
        print >> out_fh
        print_outputs(out_fh, argv, cmd.getOutputs())
        print >> out_fh
   
    make_job_outputs = job.getOutputs()
    if make_job_outputs:
        print >> out_fh, "Make Process Hierarchy:"
        print >> out_fh

        make_chain = build.getMakePath(job)
        report_make_chain(out_fh, make_chain)

        print_outputs(out_fh, None, make_job_outputs)

def print_outputs(out_fh, argv, outputs):

    # See if we shoudl not show the first output.
    # If it's just a repeated of the command argv, we've already
    # shown that.
    if argv and outputs:
        first_text = outputs[0].getText()
        # Ignore any whitespace at the beginning and end
        if first_text.strip() == argv.strip():
            outputs = outputs[1:]

    if outputs:
        print >> out_fh, "-" * 30, "Output", "-" * 30
        for i, op in enumerate(outputs):
            text = op.getText()
            # The output can contain non-ascii characters
            print >> out_fh, text.encode('utf-8'),
        print >> out_fh, "-" * (60  + len("Output") + 2)


def print_message(out_fh, n, show_summary, build, message):
    if show_summary:
        print >> out_fh, "Cluster Manager Message #%d\n" % (n,)

    build_start_dt = build.getStartDateTime()

    message_time = float(message.getTime())
    if build_start_dt:
        message_dt = build_start_dt + \
            datetime.timedelta(seconds=message_time)
    else:
        message_dt = ""

    print >> out_fh, "%s (%s) at %s (%s)" % \
            (message.getCode(), message.getSeverity(),
                    message_dt, message.getTime())
    print >> out_fh, message.getText()
    print >> out_fh

def print_header(out_fh, anno_file, build, show_summary,
        messages, error_jobs, error_makes):
    
    # Newer versions of emake have this property
    hostname = build.getProperty("UnixNodename")

    # Older versions do not, so let's look for $HOSTNAME
    if not hostname:
        hostname = build.getVar("HOSTNAME")

    print >> out_fh, "=" * 80

    if not os.path.isabs(anno_file):
        anno_file = os.path.abspath(anno_file)

    print >> out_fh, "Annotation file:\n", anno_file, "\n"
    print >> out_fh, "Build ID: %s on Host %s, Cluster Manager: %s" % \
            (build.getBuildID(), hostname, build.getCM())
    print >> out_fh, "Start Time: %s\n" % (build.getStart(),)

    if not show_summary:
        return

    # Summary information
    print >> out_fh, "Summary:"
    if messages:
        print >> out_fh, "\tCluster Manager messages:", len(messages)

    if error_jobs:
        print >> out_fh, "\tFailed commands:", len(error_jobs)

    if error_makes:
        print >> out_fh, "\tFailed Make commands:", len(error_makes)

    print >> out_fh


def print_footer(out_fh):
    print >> out_fh, "=" * 80


def report(out_fh, anno_file, build, show_summary, messages, error_jobs, error_makes):
    print_header(out_fh, anno_file, build, show_summary,
            messages, error_jobs, error_makes)

    if show_summary:
        print >> out_fh, "-" * 80

    # Details
    for i, message in enumerate(messages):
        print_message(out_fh, i+1, show_summary, build, message)
        if show_summary:
            print >> out_fh, "-" * 80

    for i, job in enumerate(error_jobs):
        print_error_job(out_fh, i+1, show_summary, build, job, TYPE_JOB)
        if show_summary:
            print >> out_fh, "-" * 80

    for i, job in enumerate(error_makes):
        print_error_job(out_fh, i+1, show_summary, build, job, TYPE_MAKE)
        if show_summary:
            print >> out_fh, "-" * 80

    print_footer(out_fh)

def Run(args):
    build = annolib.AnnotatedBuild(args.anno_file)

    # --tee only makes sense with -o
    if args.tee:
        if not args.o:
            msg = "--tee is only used with -o FILE"
            sys.exit(msg)

    if args.o:
        try:
            out_fh = open(args.o, "w")
        except IOError as e:
            sys.exit(e)
    else:
        out_fh = sys.stdout

    # We have to parse the entire file first
    error_jobs, error_makes, end_job = find_error_jobs(build)

    messages = build.getMessages()

    try:
        # If there is something to report, report it
        if messages or error_jobs or error_makes:
            num_problems = len(messages) + len(error_jobs) + len(error_makes)
            show_summary = num_problems > 1
            report(out_fh, args.anno_file, build, show_summary,
                    messages, error_jobs, error_makes)

            # Repeat the report to stdout (--tee)?
            if args.tee:
                report(sys.stdout, args.anno_file, build, show_summary,
                        messages, error_jobs, error_makes)

    except IOError as e:
        print >> sys.stderr, e

    finally:
        # Close the file
        if args.o:
            try:
                out_fh.close()
            except IOError as e:
                pass

    # Shall we exit with the same retval the build had?
    if args.exit_with_build_rc and end_job:
        sys.exit(end_job.getRetval())
