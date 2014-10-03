import sys
from pyannolib import annolib
import tyrannolib

printed_something = False

def SubParser(subparsers):

    help = "Produce a nice error report"

    parser = subparsers.add_parser("errors", help=help)
    parser.set_defaults(func=Run)

    parser.add_argument("anno_file")


def print_header(build):
    props = build.getProperties()
    print "Build ID: %s on Host %s, Cluster Manager: %s" % \
            (build.getBuildID(), props.get("UnixNodename"),
            build.getCM())
    print "Start Time: %s" % (build.getStart(),)
    print
    print "make[0] in %s" % (props.get("CWD"),)
    print props.get("CommandLine")
    print

def get_make_chain(build, job):
    make_chain = []

#    make_chain.append(job)
    parent_job = job
    parent_make = job.getMakeProcess()
    while parent_make:
        if parent_job.getStatus() == annolib.JOB_STATUS_NORMAL and \
                parent_job.getType() == annolib.JOB_TYPE_RULE:
            make_chain.insert(0, parent_make)

        parent_job_id = parent_make.getParentJobID()
        parent_job = build.getMakeJob(parent_job_id)
        if not parent_job:
            # The top-most, initial Make won't have a parent
            # job, and we won't have inserted it already, so insert
            # it now into the chain.
            #make_chain.insert(0, parent_make)
            break

        parent_make = parent_job.getMakeProcess()

    return make_chain

def report_make_chain(chain):
    for i, make_proc in enumerate(chain):
        print "%s make[%s] in %s" % (make_proc.getID(),
                make_proc.getLevel(), make_proc.getCWD())
        print make_proc.getCmd()
        print

def cb(job, build):
    global printed_something

    if job.getType() != annolib.JOB_TYPE_RULE:
        return

    if job.getRetval() == job.SUCCESS:
        return

    printed_something = True
    print "=" * 80

    make_proc = job.getMakeProcess()

    print "Job ID: %s , Exit Value %s" % (job.getID(), job.getRetval())
    print "CWD: %s" % (make_proc.getCWD(),)
    for timing in job.getTimings():
        print "Node: %s Start:%s End:%s" % (timing.getNode(),
                timing.getInvoked(), timing.getCompleted())
    print

    for cmd in job.getCommands():
        print "Command:"
        argv = cmd.getArgv()
        print argv
        print
        print "---Output-----------------------------------------------------"
        for i, op in enumerate(cmd.getOutputs()):
            text = op.getText()
            if i == 0 and text == argv + "\n":
                # If Make prints the command (no "@" at the beginning
                # of the line in the action), it will look just like argv,
                # so let's avoid printing it again here.
                continue
            else:
                print text,

        print "--------------------------------------------------------------"

#    for output in job.getOutputs():
#        print op.getText()

    print
    print "Make Process Hierarchy:"
    print

    make_chain = get_make_chain(build, job)
    report_make_chain(make_chain)



def Run(args):
    build = annolib.AnnotatedBuild(args.anno_file)

    print_header(build)

    build.parseJobs(cb, build)

    if printed_something:
        print "=" * 80
