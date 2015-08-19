# Copyright (c) 2013 by Cisco Systems, Inc.
"""
Handle the emake annotation file.
"""
from pyannolib import concatfile
import re
import datetime
import os

try:
    # Try to import the C-based ElementTree (faster!)
    from xml.etree import cElementTree as ET
except ImportError:
    # But use the Python-based ElementTree if necessary
    from xml.etree import ElementTree as ET


# Job status values
JOB_STATUS_NORMAL = "normal"
JOB_STATUS_RERUN = "rerun"
JOB_STATUS_CONFLICT = "conflict"
JOB_STATUS_REVERTED = "reverted"
JOB_STATUS_SKIPPED = "skipped"

# Job type values
JOB_TYPE_CONTINUATION = "continuation"
JOB_TYPE_END = "end"
JOB_TYPE_EXIST = "exist"
JOB_TYPE_EXTERNAL = "external"
JOB_TYPE_FOLLOW = "follow"
JOB_TYPE_PARSE = "parse"
JOB_TYPE_REMAKE = "remake"
JOB_TYPE_RULE = "rule"
JOB_TYPE_SUBBUILD = "subbuild"
JOB_TYPE_ALPHA = "alpha"
JOB_TYPE_OMEGA = "omega"
JOB_TYPE_UPDATE = "update"
JOB_TYPE_STATCACHE = "statcache"

# Dep type values
DEP_TYPE_FILE = "file"
DEP_TYPE_KEY = "key"
DEP_TYPE_VALUE = "value"

# Op type values
OP_TYPE_LOOKUP = "lookup"
OP_TYPE_READ = "read"
OP_TYPE_CREATE = "create"
OP_TYPE_MODIFY = "modify"
OP_TYPE_UNLINK = "unlink"
OP_TYPE_RENAME = "rename"
OP_TYPE_LINK = "link"
OP_TYPE_MODIFYATTRS = "modifyAttrs"
OP_TYPE_APPEND = "append"
OP_TYPE_BLINDCREATE = "blindcreate"
OP_TYPE_SUBMAKE = "submake"

# Op filetype values
OP_FILETYPE_FILE = "file"
OP_FILETYPE_SYMLINK = "symlink"
OP_FILETYPE_DIR = "dir"

# Op booleans
OP_FOUND_TRUE = "1"
OP_FOUND_FALSE = "0"
OP_ISDIR_TRUE = "1"
OP_ISDIR_FALSE = "0"

# Output sources
OUTPUT_SRC_PROG = "prog"
OUTPUT_SRC_MAKE = "make"


# Message severities
MESSAGE_SEVERITY_WARNING = "warning"
MESSAGE_SEVERITY_ERROR = "error"

# Some error strings
MSG_UNEXPECTED_XML_ELEM = "Unexpected xml element: "

# This value is returned by the parseJobs callback if
# the caller wants parsing to stop. There is no way to re-start it.
StopParseJobs = 1

class PyAnnolibError(Exception):
    """Generic exception for any error this library wants
    to pass back to the client"""
    pass


###################################################

class AnnoXMLNames:
    """These constants are used by any class that is parsing 
    the annotation XML."""

    # Found in the "header"
    ELEMENT_BUILD = "build"
    ELEMENT_PROPERTIES = "properties"
    ELEMENT_PROPERTY = "property"
    ELEMENT_ENVIRONMENT = "environment"
    ELEMENT_VAR = "var"
    ATTR_PROP_NAME = "name"
    ATTR_VAR_NAME = "name"

    # Found in the metrics "footer"
    ELEMENT_METRIC = "metric"
    ATTR_METRIC_NAME = "name"

    # Found in the "body"
    ELEMENT_MAKE = "make"
    ELEMENT_JOB = "job"
    ELEMENT_OUTPUT = "output"
    ELEMENT_OPLIST = "opList"
    ELEMENT_OP = "op"
    ELEMENT_METRICS = "metrics"
    ELEMENT_METRIC = "metric"
    ELEMENT_TIMING = "timing"
    ELEMENT_WAITING_JOBS = "waitingJobs"
    ELEMENT_COMMAND = "command"
    ELEMENT_ARGV = "argv"
    ELEMENT_OUTPUT = "output"
    ELEMENT_DEPLIST = "depList"
    ELEMENT_DEP = "dep"
    ELEMENT_FAILED = "failed"
    ELEMENT_CONFLICT = "conflict"
    ELEMENT_MESSAGE = "message"
    ELEMENT_COMMIT_TIMES = "commitTimes"

    # These attributes are handled by the AnnoXMLBodyParser directly
    ATTR_WAITINGJOBS_IDLIST = "idList"
    ATTR_METRIC_NAME = "name"
    ATTR_OUTPUT_SRC = "src"
    ATTR_FAILED_CODE = "code"



###################################################



class AnnotatedBuild(AnnoXMLNames):
    ID = "id"
    CM = "cm"
    START = "start"
    LOCAL_AGENTS = "localAgents"

    def __init__(self, filename, fh=None):
        """Can raise IOError"""
        # Initialize this since it is used in __str
        self.build_id = None
        
        # Other fields to initialize
        self.cm = None
        self.start_text = None
        self.local_agents = None

        # Key = property name, Value = property value (string)
        self.properties = {}

        # Key = env var name, Value = env var value (string)
        self.vars = {}

        # Key = metric name, Value = metric value (string)
        self.metrics = {}

        # This is initialized now, but won't be filled in until
        # the message records are seen while processing jobs
        self.messages = []

        # All MakeProcesses.
        # Key = make proc ID, Value = MakeProcess object
        self.make_procs = {}

        # Jobs that spawned MakeProcesses
        # Key = job ID, value = Job object
        self.make_jobs = {}

        if filename:
            assert not fh, "filename and fh both given"

            # Allow the exception to go back to the caller of AnnoFileParser
            try:
                self.fh = anno_open(filename)
            except (IOError, ValueError) as e:
                raise PyAnnolibError(e)

        elif fh:
            self.fh = fh

        else:
            assert 0, "Neither filename or fh given"

        # Parse the header
        self._parse_header()

        # Now, skip to the end of the file and look for metrics.
        self._parse_metrics()

        # Set the filehandle back to the beginning; when parseJobs()
        # is run, it uses AnnoXMLBodyParser, which skips over all the XML
        # fields that are part of the header. It's not the most efficient
        # way to handle the separation of body and header; it would be
        # much nicer to skip over the header and start parsing where
        # the body starts. Maybe we'll do that in the future.
        self.fh.seek(0, os.SEEK_SET)

    def close(self):
        """Closes the filehandle, which may be needed if you had
        AnnotatedBuild open() it for you."""
        assert self.fh, "fh has no value"
        self.fh.close()

    def __str__(self):
        return "<AnnotatedBuild id=%s>" % (self.build_id,)


    def _parse_header(self):
        # Read the complete header into a string
        header_text = self._read_header()

        # Add a fake </build> to end it
        header_text += "</build>"

        # Parse the XML string
        try:
            root = ET.fromstring(header_text)
        except ET.ParseError, e:
            msg = "Error parsing header XML: %s" % (e,)
            raise PyAnnolibError(msg)

        # Get the 'build' data (root XML node)
        self.build_id = root.attrib.get(self.ID)
        self.cm = root.attrib.get(self.CM)
        self.start_text = root.attrib.get(self.START)
        self.local_agents = root.attrib.get(self.LOCAL_AGENTS)

        # Store the data from the rest of the header
        for elem in list(root):
            if elem.tag == self.ELEMENT_PROPERTIES:
                for prop_elem in list(elem):
                    if prop_elem.tag == self.ELEMENT_PROPERTY:
                        prop_name = prop_elem.get(self.ATTR_PROP_NAME)
                        self.properties[prop_name] = prop_elem.text
                    else:
                        msg = "Unexpected element in <properties>: %s" % \
                                (prop_elem.tag,)
                        raise PyAnnolibError(msg)

            elif elem.tag == self.ELEMENT_ENVIRONMENT:
                for var_elem in list(elem):
                    if var_elem.tag == self.ELEMENT_VAR:
                        var_name = var_elem.get(self.ATTR_VAR_NAME)
                        self.vars[var_name] = var_elem.text
                    else:
                        msg = "Unexpected element in <environment>: %s" % \
                                (var_elem.tag,)
                        raise PyAnnolibError(msg)

            else:
                msg = "Unexpected element in <build>: %s" % (elem.tag,)
                raise PyAnnolibError(msg)


    def _read_header(self):
        # Read chunks of the file until we find the
        # first <message> or <make> record
        # I suspect only <make> can come first, but who knows?
        BYTES_TO_READ = 32768
        header_text = ""

        re_start = re.compile(r"(?P<start><message|<make)")

        start_pos = 0
        while True:
            new_data = self.fh.read(BYTES_TO_READ)
            # EOF?
            if new_data == "":
                msg = "Did not find end of header"
                raise PyAnnolibError(msg)

            # Can we see the first thing after the header?
            header_text += new_data
            m = re_start.search(header_text, start_pos)
            if m:
                i = m.start("start")
                return header_text[:i]
            else:
                # On the next loop we will read more data
                # but let's increment start_pos by a value less
                # than BYTES_TO_READ so that in case the string
                # was split between this read and the next read
                # we will still find it. The maximum string size
                # is len("<message"), which is 8. Thus,
                # we should start scanning at BYTES_TO_READ - ( 8 - 1 )
                start_pos += (BYTES_TO_READ - 7)


    def _parse_metrics(self):
        metrics_text = self._read_metrics_footer()
        if not metrics_text:
            return

        # Parse the XML string
        try:
            root = ET.fromstring(metrics_text)
        except ET.ParseError, e:
            msg = "Error reading <metrics>: %s" % (e,)
            raise PyAnnolibError(msg)

        # Store the data in our dictionary
        for elem in list(root):
            if elem.tag == self.ELEMENT_METRIC:
                metric_name = elem.get(self.ATTR_METRIC_NAME)
                self.metrics[metric_name] = elem.text
            else:
                msg = MSG_UNEXPECTED_XML_ELEM + elem.tag
                raise PyAnnolibError(msg)

    def _read_metrics_footer(self):
        """Returns the text of the <metrics></metrics> block of XML.
        Or, returns None if it is missing."""
        # Number of bytes to skip backwards at a time.
        # In my tests, the metrics section is ~3000 bytes.
        SKIP_NUM_BYTES = 500
        ELEM_STRING_START_METRICS = "<metrics>"
        ELEM_STRING_END_METRICS = "</metrics>"
        ELEM_STRING_END_JOB = "</job>"
        
        # When reading, we want to read more than what we just
        # skipped, so that if half the string is in one chunk, and
        # half the string is in the next chunk, we are sure to find
        # the string.
        READ_CHUNK_NUM_BYTES = SKIP_NUM_BYTES + len(ELEM_STRING_START_METRICS)

        # Go to EOF
        self.fh.seek(0, os.SEEK_END)

        pos = self.fh.tell()

        # Go back in chunks, until we find "<metrics>"
        pos -= SKIP_NUM_BYTES
        self.fh.seek(pos, os.SEEK_SET)
        while pos >= 0:
            data = self.fh.read(READ_CHUNK_NUM_BYTES)
            i = data.find(ELEM_STRING_START_METRICS)
            if i == -1:
                # Didn't find it. Are there any other indications
                # that we have gone too far? If we see a job, then yes.
                if data.find(ELEM_STRING_END_JOB) != -1:
                    return None
                else:
                    pos -= SKIP_NUM_BYTES
                    self.fh.seek(pos, os.SEEK_SET)
            else:
                # We found it; stop looping
                break

        # We found "<metrics>". Let's read the whole "<metrics>"
        # section into memory. First, position the filehandle
        # to the place where "<metrics>" starts, then read to EOF.
        self.fh.seek(pos + i, os.SEEK_SET)
        metrics_text = self.fh.read()

        # We need to trim the stuff after "</metrics>",
        # which should be "</build>"
        i = metrics_text.find(ELEM_STRING_END_METRICS)
        if i == -1:
            msg = "Found %s but not %s" % (ELEM_STRING_START_METRICS,
                    ELEM_STRING_END_METRICS)
            raise PyAnnolibError(msg)

        metrics_text = metrics_text[:i + len(ELEM_STRING_END_METRICS)]
        return metrics_text


    def addMessage(self, msg):
        self.messages.append(msg)

    def getCM(self):
        return self.cm

    def getStart(self):
        return self.start_text

    def getLocalAgents(self):
        return self.local_agents

    def getStartDateTime(self):
        """Returns a datetime.datetime object that represents
        the start time of the build. Note that we do not take into
        account the timezone, even though it is present in the
        start time string in the annotation file. 
        This will return None if the date cannot be decoded."""

        # I have seen different formats, and my concern is that
        # it might even be local-specific :(
        formats = [
            # Example: Thu 02 Oct 2014 12:16:53 PM PDT
            "%a %d %b %Y %I:%M:%S %p %Z",

            # Example: Tue Nov 25 20:01:46 2014
            "%a %b %d %H:%M:%S %Y",
        ]
        for fmt in formats:
            try:
                return datetime.datetime.strptime(self.start_text, fmt)
            except ValueError:
                # the strptime format didn't match. Keep trying
                continue
        else:
            return None

    def getBuildID(self):
        return self.build_id

    def getProperties(self):
        return self.properties

    def getProperty(self, name):
        return self.properties.get(name)

    def getVars(self):
        return self.vars

    def getVar(self, name):
        return self.vars.get(name)

    def getMetrics(self):
        return self.metrics

    def getMetric(self, name):
        return self.metrics.get(name)

    def getMessages(self):
        return self.messages

    def addMakeProcess(self, make_elem):
        make_id = make_elem.getID()
        assert make_id not in self.make_procs
        self.make_procs[make_id] = make_elem

    def getMakeProcess(self, make_id):
        return self.make_procs.get(make_id)

    def addMakeJob(self, job):
        # For Make #0, we will be passed None for job,
        # so check for that.
        if job:
            job_id = job.getID()
            assert job_id not in self.make_jobs
            self.make_jobs[job_id] = job

    def getMakeJob(self, job_id):
        return self.make_jobs.get(job_id)

    def getMakePath(self, job):
        """This is just like getJobPath, but returns only
        the MakeProcess objects."""
        return [ obj for obj in self.getJobPath(job) if
                isinstance(obj, MakeProcess) ]

    def getJobPath(self, job):
        """Returns a list of MakeProcess and Job objects, which
        correspond to the "Job Path" tab for a job in Electric
        Insight. It is the chain of jobs from the first MakeProc
        down to job itself. The items alternate by MakeProc,
        which represents a sub-make, and a Job, which is make
        rule job or parse job, until you finally get to the
        job that was passed in.

        The first item in the list is the root MakeProc
        (M00000000), and the last item is the job that was
        passed in to getJobPath.
        """
       
        assert isinstance(job, Job)

        job_chain = []

        # Start from the job given to us, pretending it
        # was the last job we looked ad.
        this_job = job
        parent_make = job.getMakeProcess()

        # The Job Path reported by Electric Insight shows
        # these types of jobs (but this list might not
        # be complete)
        OK_TYPES = [JOB_TYPE_RULE, JOB_TYPE_PARSE]

        # The Job Path reported by Electric Insight shows
        # jobs with these statuses (but this list might not
        # be complete)
        OK_STATUSES = [JOB_STATUS_NORMAL, JOB_STATUS_RERUN]

        while parent_make:
            if this_job.getType() in OK_TYPES and \
                    this_job.getStatus() in OK_STATUSES:
                job_chain.insert(0, this_job)
                job_chain.insert(0, parent_make)

            parent_job_id = parent_make.getParentJobID()
            this_job = self.getMakeJob(parent_job_id)

            # The top-most, initial Make won't have a parent job.
            # That's our condition to stop the loop!
            if not this_job:
                break

            parent_make = this_job.getMakeProcess()

        return job_chain

    def getAllJobs(self):
        """Gather all Job records in a list and return that list.
        It's a convenience function; the same could be done via parseJobs()
        and the appropriate callback."""

        jobs = [job for job in self.iterJobs()]

        return jobs

    def parseJobs(self, cb, user_data=None):
        """Like iterJobs, but calls a callback function as cb(job, user_data).
        If the callback returns StopParseJobs, the iteration stops."""
        for job in self.iterJobs():
            retval = cb(job, user_data)
            if retval == StopParseJobs:
                break

    def iterJobs(self):
        """Parse jobs and yield one Job at a time."""
        if not self.fh:
            raise PyAnnolibError("filehandle was not set in Build object")

        # Create the parser
        parser = AnnoXMLBodyParser(self)

        # Parse the file
        return parser.parse(self.fh)


####################################################

        


class MakeProcess:

    LEVEL = "level"
    CMD = "cmd"
    CWD = "cwd"
    OWD = "owd"
    MODE = "mode"

    def __init__(self, elem, make_proc_num, parser):
        self.level = elem.get(self.LEVEL)
        self.cmd = elem.get(self.CMD)
        self.cwd = elem.get(self.CWD)
        self.owd = elem.get(self.OWD) # implied, not required
        self.mode = elem.get(self.MODE)

        # This is not stored as a field in the XML file; it is
        # constructed by noting the sequential order of <job>'s
        # and <make>'s  in the file. The <job> just previous to
        # a <make> is the <make>'s parent job.
        self.parent_job_id = None

        self.make_proc_id = "M%08x" % (make_proc_num,)


    def __str__(self):
        return "<MakeProcess level=%s cwd=%s>" % (self.level, self.cwd)

    def setParentJobID(self, job_id):
        self.parent_job_id = job_id

    def getLevel(self):
        return self.level

    def getCmd(self):
        return self.cmd

    def getCWD(self):
        return self.cwd

    def getOWD(self):
        return self.owd

    def getMode(self):
        return self.mode

    def getParentJobID(self):
        return self.parent_job_id

    def getID(self):
        return self.make_proc_id

    def getTextReport(self):
        text = "%s make[%s], CWD=%s\n" % (self.make_proc_id,
                self.level, self.cwd)
        text += self.cmd
        return text

class Job(AnnoXMLNames):

    ID = "id"
    STATUS  ="status"
    THREAD = "thread"
    TYPE = "type"
    NAME = "name"
    NEEDED_BY = "neededby"
    LINE = "line"
    FILE = "file"
    SUCCESS = 0
    PARTOF = "partof"   # for FOLLOW-type jobs

    def __init__(self, elem):
        self.job_id = elem.get(self.ID)
        self.status = elem.get(self.STATUS, JOB_STATUS_NORMAL)
        self.thread = elem.get(self.THREAD)
        self.type = elem.get(self.TYPE)
        self.name = elem.get(self.NAME)
        self.needed_by = elem.get(self.NEEDED_BY)
        self.line = elem.get(self.LINE)
        self.file = elem.get(self.FILE)
        self.partof = elem.get(self.PARTOF)

        self.outputs = []
        self.make = None
        self.timings = []
        self.oplist = []
        self.waiting_jobs = []
        self.commands = []
        self.deplist = []
        self.conflict = None
        self.vars = {}
        self.commit_times = None

        # The return value of the Job. By default
        # we assume success, but a <failed> record overrides that.
        self.retval = self.SUCCESS

        for child_elem in list(elem):
            if child_elem.tag == self.ELEMENT_TIMING:
                timing = Timing(child_elem)
                self.timings.append(timing)

            elif child_elem.tag == self.ELEMENT_OPLIST:
                self.parseOpList(child_elem)

            elif child_elem.tag == self.ELEMENT_WAITING_JOBS:
                self.parseWaitingJobs(child_elem)

            elif child_elem.tag == self.ELEMENT_COMMAND:
                command = Command(child_elem)
                self.commands.append(command)

            elif child_elem.tag == self.ELEMENT_OUTPUT:
                # This is the job output, not the command output
                output_src = child_elem.get(self.ATTR_OUTPUT_SRC,
                        OUTPUT_SRC_MAKE)
                output = Output(child_elem.text, output_src)
                self.outputs.append(output)

            elif child_elem.tag == self.ELEMENT_FAILED:
                code_text = child_elem.get(self.ATTR_FAILED_CODE)
                self.retval = int(code_text)

            elif child_elem.tag == self.ELEMENT_CONFLICT:
                self.conflict = Conflict(child_elem)

            elif child_elem.tag == self.ELEMENT_DEPLIST:
                self.parseDepList(child_elem)

            elif child_elem.tag == self.ELEMENT_ENVIRONMENT:
                for var_elem in list(child_elem):
                    if var_elem.tag == self.ELEMENT_VAR:
                        var_name = var_elem.get(self.ATTR_VAR_NAME)
                        self.vars[var_name] = var_elem.text
                    else:
                        msg = "Unexpected element in <environment>: %s" % \
                                (var_elem.tag,)
                        raise PyAnnolibError(msg)

            elif child_elem.tag == self.ELEMENT_COMMIT_TIMES:
                self.commit_times = CommitTimes(child_elem)

            else:
                assert False, MSG_UNEXPECTED_XML_ELEM + child_elem.tag

    def __str__(self):
        return "<Job id=%s>" % (self.job_id,)

    def parseOpList(self, elem):
        for child_elem in list(elem):
            if child_elem.tag == self.ELEMENT_OP:
                op = Operation(child_elem)
                self.oplist.append(op)

            else:
                assert False, MSG_UNEXPECTED_XML_ELEM + child_elem.tag

    def parseDepList(self, elem):
        for child_elem in list(elem):
            if child_elem.tag == self.ELEMENT_DEP:
                dep = Dependency(child_elem)
                self.deplist.append(dep)

            else:
                assert False, MSG_UNEXPECTED_XML_ELEM + child_elem.tag

    def parseWaitingJobs(self, elem):
        ids_string = elem.get(self.ATTR_WAITINGJOBS_IDLIST)

        # The job IDs are space-delimited in the string;
        # use split() to create a list
        self.waiting_jobs = ids_string.split()

    def setMakeProcess(self, make_elem):
        self.make = make_elem

    def getID(self):
        return self.job_id

    def getStatus(self):
        return self.status

    def getThread(self):
        return self.thread

    def getType(self):
        return self.type

    def getOutputs(self):
        return self.outputs

    def getOperations(self):
        return self.oplist

    def getMakeProcess(self):
        return self.make

    def getTimings(self):
        return self.timings

    def getWaitingJobs(self):
        return self.waiting_jobs

    def getCommands(self):
        return self.commands

    def getCommitTimes(self):
        return self.commit_times

    def getDependencies(self):
        return self.deplist

    def getRetval(self):
        return self.retval

    def getConflict(self):
        return self.conflict

    def getName(self):
        return self.name

    def getNeededBy(self):
        return self.needed_by

    def getFile(self):
        return self.file

    def getLine(self):
        return self.line

    def getPartOf(self):
        return self.partof

    def getVars(self):
        return self.vars

    def getVar(self, name):
        return self.vars.get(name)

    def getTextReport(self):
        text = """Job ID:    %s
Type:      %s
Status:    %s
Thread:    %s
""" % (self.job_id, self.type, self.status, self.thread)

        if self.name:
            text += "Name:      %s\n" % (self.name,)

        if self.file:
            text += "File:      %s\n" % (self.file,)

        if self.line:
            text += "Line:      %s\n" % (self.line,)

        if self.needed_by:
            text += "Needed By: %s\n" % (self.needed_by,)

        if self.partof:
            text += "Part Of:   %s\n" % (self.partof,)

        if self.make:
            text += "Make Proc: make[%s]: %s, CWD=%s\n" % \
                    (self.make.getLevel(), self.make.getID(),
                        self.make.getCWD())

        if self.conflict:
            text += "Conflict:\n"
            text += self.conflict.getTextReport()
            text += "\n"

        if self.commitTimes:
            text += "Commands:\n"
            text += self.commitTimes.getTextReport()
            text += "\n"

        if self.timings:
            text += "Timings:\n"
            for timing in self.timings:
                text += timing.getTextReport()
            text += "\n"

        if self.waiting_jobs:
            WAITING_JOB = "Waiting Jobs: "
            LEN_WAITING_JOB = len(WAITING_JOB)
            text += WAITING_JOB
            i = 0
            
            # Did we jus start a new line? True/False
            carriage_return = False

            for (i, waiting_job) in enumerate(self.waiting_jobs):
                # If we did just start a new line, shift over first.
                if carriage_return == True:
                    text += " " * LEN_WAITING_JOB
                    carriage_return = False
                elif i > 0:
                    # No? then shift over just one space
                    # (except if this is the very first item)
                    text += " "

                # Add the job id
                text += waiting_job

                # If we printed 3 jobs, the next loop needs to start
                # on a new line.
                if i > 0 and (i + 1) % 3 == 0:
                    carriage_return = True
                    text += "\n"

            # Do we need a final new-line?
            if not carriage_return:
                text += "\n"

        text += "\n"
        if self.commands:
            text += "Commands:\n"
            for command in self.commands:
                text += command.getTextReport()


        if self.outputs:
            text += "Outputs:\n"
            for output in self.outputs:
                text += output.getTextReport()
            text += "\n"

        if self.deplist:
            text += "Dependencies:\n\n"
            for dep in self.deplist:
                text += dep.getTextReport()

        if self.oplist:
            text += "Operations:\n\n"
            for op in self.oplist:
                text += op.getTextReport()

        return text

#    def __getstate__(self):
#        return (
#                self.job_id,
#                self.status,
#                self.thread,
#                self.type,
#                self.name,
#                self.needed_by,
#                self.line,
#                self.file,
#                self.partof,
#                self.outputs,
#                self.make.getID(), # store the MakeProcess ID
#                self.timings,
#                self.oplist,
#                self.waiting_jobs,
#                self.commands,
#                self.deplist,
#                self.conflict,
#                self.retval,
#                )
#
#    def __setstate__(self, state):
#        (
#            self.job_id,
#            self.status,
#            self.thread,
#            self.type,
#            self.name,
#            self.needed_by,
#            self.line,
#            self.file,
#            self.partof,
#            self.outputs,
#            self.make_id,
#            self.timings,
#            self.oplist,
#            self.waiting_jobs,
#            self.commands,
#            self.deplist,
#            self.conflict,
#            self.retval,
#        ) = state
#        
#        self.make = None
#
#    def fix_unpickled_state(self, make_proc_hash):
#        if self.make_id:
#            self.make =  make_proc_hash.get(self.make_id)
#            del self.make_id


class Operation:
    TYPE = "type"
    FILE = "file"
    FILETYPE = "filetype"
    FOUND = "found"
    ISDIR = "isdir"

    def __init__(self, elem):
        self.type = elem.get(self.TYPE)
        self.file = elem.get(self.FILE)
        self.filetype = elem.get(self.FILETYPE, OP_FILETYPE_FILE)
        self.found = elem.get(self.FOUND, OP_FOUND_TRUE)
        self.isdir = elem.get(self.ISDIR, OP_ISDIR_TRUE)

    def getType(self):
        return self.type

    def getFile(self):
        return self.file

    def getFileType(self):
        return self.filetype

    def getFound(self):
        return self.found

    def getTextReport(self):
        if self.found == "1":
            found = "found"
        else:
            found = "not-found"
        text  = "(%s,%s,%s) %s\n" % (self.type, self.filetype, found, self.file)
        return text


class Timing:
    INVOKED = "invoked"
    COMPLETED = "completed"
    NODE = "node"

    def __init__(self, elem):
        self.invoked = elem.get(self.INVOKED)
        self.completed = elem.get(self.COMPLETED)
        self.node = elem.get(self.NODE)

    def getInvoked(self):
        return self.invoked

    def getCompleted(self):
        return self.completed

    def getNode(self):
        return self.node

    def getTextReport(self):

        try:
            duration = float(self.completed) - float(self.invoked)
        except ValueError:
            duration = None

        text = " Node: %s " % (self.node,)
        padding = "        " + " " * len(self.node,)
        text += "Invoked:    %15s sec\n" % (self.invoked, )
        text += padding + "Completed:  %15s sec\n" % (self.completed, )
        text += padding + "Duration:   %15s sec\n" % (duration, )

        return text


class Command(AnnoXMLNames):
    LINE = "line"

    def __init__(self, elem):
        # "line" is optional
        self.line = elem.get(self.LINE)
        self.argv = ""
        self.outputs = []

        for child_elem in list(elem):
            if child_elem.tag == self.ELEMENT_ARGV:
                assert not self.argv
                self.argv = child_elem.text

            elif child_elem.tag == self.ELEMENT_OUTPUT:
                # This is the command output, not the job output
                output_src = child_elem.get(self.ATTR_OUTPUT_SRC,
                        OUTPUT_SRC_MAKE)
                output = Output(child_elem.text, output_src)
                self.outputs.append(output)

            else:
                assert False, MSG_UNEXPECTED_XML_ELEM + child_elem.tag

    def getLine(self):
        return self.line

    def getArgv(self):
        return self.argv

    def getOutputs(self):
        return self.outputs

    def getTextReport(self):
        text = "Line: %s\n" % (self.line,)
        text += self.argv + "\n"
        for output in self.outputs:
            text += output.getTextReport()
        return text

class Output:
    def __init__(self, text, src):
        self.text = text
        self.src = src

    def getText(self):
        return self.text

    def getSrc(self):
        return self.src

    def getTextReport(self):
        text_report  = "------- Output (%s) -------" % (self.src,)
        if self.text[0] != "\n":
            text_report += "\n"
        text_report += self.text
        text_report += "--------%s-----------------\n" % ("-" * len(self.src),)
        return text_report


class Dependency:
    WRITE_JOB = "writejob"
    FILE = "file"
    TYPE = "type"

    def __init__(self, elem):
        self.write_job = elem.get(self.WRITE_JOB)
        self.file = elem.get(self.FILE)
        self.type = elem.get(self.TYPE, DEP_TYPE_FILE)

    def getWriteJob(self):
        return self.write_job

    def getFile(self):
        return self.file

    def getType(self):
        return self.type

    def getTextReport(self):
        text  = "File: %s\n" % (self.file,)
        text += "Type: %s WriteJob: %s\n\n" % (self.type, self.write_job)
        return text

class Conflict:
    TYPE = "type"
    WRITE_JOB = "writejob"
    FILE = "file"
    RERUN_BY = "rerunby"

    def __init__(self, elem):
        self.type = elem.get(self.TYPE)
        self.write_job = elem.get(self.WRITE_JOB)
        self.file = elem.get(self.FILE)
        self.rerun_by = elem.get(self.RERUN_BY)

    def getType(self):
        return self.type

    def getWriteJob(self):
        return self.write_job

    def getFile(self):
        return self.file

    def getRerunBy(self):
        return self.rerun_by

    def getTextReport(self):
        return """File: %s
Type: %s
Write Job: %s
Rerun By: %s
""" % (self.file, self.type, self.write_job, self.rerun_by)


class CommitTimes:
    START = "start"
    WAIT = "wait"
    COMMIT = "commit"
    WRITE = "write"

    def __init__(self, elem):
        self.start = elem.get(self.START)
        self.wait = elem.get(self.WAIT)
        self.commit = elem.get(self.COMMIT)
        self.write = elem.get(self.WRITE)

    def getStart(self):
        return self.start

    def getWait(self):
        return self.wait

    def getCommit(self):
        return self.commit

    def getWrite(self):
        return self.write

    def getTextReport(self):
        return """Start: %s
Wait: %s
Commit: %s
Write: %s
""" % (self.start, self.wait, self.commit, self.write)


class Message:
    THREAD = "thread"
    TIME = "time"
    SEVERITY = "severity"
    CODE = "code"

    def __init__(self, elem):
        self.thread = elem.get(self.THREAD)
        self.time = elem.get(self.TIME)
        self.severity = elem.get(self.SEVERITY)
        self.code = elem.get(self.CODE)
        self.text = elem.text

    def setText(self, text):
        self.text = text

    def getText(self):
        return self.text

    def getThread(self):
        return self.thread

    def getTime(self):
        return self.time

    def getSeverity(self):
        return self.severity

    def getCode(self):
        return self.code


class AnnoXMLBodyParser(AnnoXMLNames):

    def __init__(self, build):
        self.build = build
        self.chars = ""
        self.indent = 0

        # In local mode builds, make elements can nest,
        # so this list of make_elem's is a stack.
        self.make_elems = []

        # The previous job element that was completely parsed
        # This is needed to associate a "parent" job to a MakeProcess
        self.prev_job_elem = None

        # Make processes don't have ID's in the XML file. We give
        # them sequential ID's according to the order we discover
        # them in the XML file. The root <make> is #0.
        self.make_proc_num = 0

        self.metrics = {}


    def parse(self, fh, use_generator=False):
    
        # The XML looks like this:
        # <make>
        #   <job></job>
        #   <job></job>
        #   <make>
        #       <job></job>
        #       <job></job>
        #       <make>
        #           <job></job>
        #           <job></job>
        #       </make>
        #       <job></job>
        #   </make>
        #   <job></job>
        # <make>
        #
        # We want to grab the end of a <job> element, so we
        # can parse it fully and send it back to the user.
        # But we want to grab the start and end of a <make> element,
        # so that we know which MakeProcess a Job belongs to.
        # The last thing we want is to read the entire <make> tree
        # into memory, which will read in all the jobs!

        # http://effbot.org/zone/element-iterparse.htm#incremental-parsing
        START_EVENT = "start"
        END_EVENT = "end"
        icontext = ET.iterparse(fh, events=(START_EVENT, END_EVENT))

        # Turn the context into an iterator
        context = iter(icontext)

        # Get the root element
        event, root = context.next()

        #for action, elem in ET.iterparse(fh):
        for event, elem in context:
            if event == START_EVENT:
                if elem.tag == self.ELEMENT_MAKE:
                    self.startMake(elem)
                    continue
                else:
                    # Skip all other START events
                    continue

            # Everything else is an END event
            def call_yield(job):
                yield job

            if elem.tag == self.ELEMENT_JOB:
                assert len(self.make_elems) > 0
                job = Job(elem)

                job.setMakeProcess(self.make_elems[-1])

                # Send the Job back to the user
                yield job

                # Set the "previous job" to this job, so that
                # we know which job begins a Make process.
                self.prev_job_elem = job

            elif elem.tag == self.ELEMENT_MESSAGE:
                msg = Message(elem)
                self.build.addMessage(msg)

            elif elem.tag == self.ELEMENT_MAKE:
                assert len(self.make_elems) > 0
                self.make_elems.pop()

            # Explicitly skip elements that are sub-elements
            # of Job
            elif elem.tag == self.ELEMENT_TIMING:
                continue
            elif elem.tag == self.ELEMENT_OPLIST:
                continue
            elif elem.tag == self.ELEMENT_OP:
                continue
            elif elem.tag == self.ELEMENT_ARGV:
                continue
            elif elem.tag == self.ELEMENT_OUTPUT:
                continue
            elif elem.tag == self.ELEMENT_COMMAND:
                continue
            elif elem.tag == self.ELEMENT_WAITING_JOBS:
                continue
            elif elem.tag == self.ELEMENT_FAILED:
                continue
            elif elem.tag == self.ELEMENT_CONFLICT:
                continue
            elif elem.tag == self.ELEMENT_DEPLIST:
                continue
            elif elem.tag == self.ELEMENT_DEP:
                continue
            elif elem.tag == self.ELEMENT_COMMIT_TIMES:
                continue

            # Explicitly skip the elements found only in the metrics
            elif elem.tag == self.ELEMENT_METRIC:
                continue

            # Explicitly skip the elements found only in the header
            elif elem.tag == self.ELEMENT_PROPERTIES:
                continue
            elif elem.tag == self.ELEMENT_PROPERTY:
                continue
            elif elem.tag == self.ELEMENT_ENVIRONMENT:
                continue
            elif elem.tag == self.ELEMENT_VAR:
                continue

            # We handled metrics at the beginning of
            # the parse
            elif elem.tag == self.ELEMENT_METRICS:
                continue

            # Explicitly skip ourself!
            elif elem.tag == self.ELEMENT_BUILD:
                continue

            # Catch my mistakes
            else:
                assert False, MSG_UNEXPECTED_XML_ELEM + elem.tag

            # If we reached here, we processed an END event for an element.
            # Free the memory for this element
            elem.clear()


    def startMake(self, elem):
        make_elem = MakeProcess(elem, self.make_proc_num, self)

        self.make_proc_num += 1

        # All <make>'s must be preceded by a <job>, except for the
        # first make. If emake was run from the command-line, it's 0,
        # but if emake was run from inside a parent GNU Make,
        # then it's > 0. In order to see if this is the "root"
        # emake process, we cannot rely on getLevel(), as it could
        # be _anything_, so we simply check if it is the first
        # "<make>" element we found in the annotation file.
        if self.make_proc_num > 1:
            assert self.prev_job_elem
            if self.prev_job_elem.getType() == JOB_TYPE_FOLLOW:
                make_elem.setParentJobID(self.prev_job_elem.getPartOf())
            else:
                make_elem.setParentJobID(self.prev_job_elem.getID())

        self.make_elems.append(make_elem)
        self.build.addMakeProcess(make_elem)
        self.build.addMakeJob(self.prev_job_elem)




def anno_open(filename, mode="rb"):
    """Return either a Python file object, if there is only one
    annotation file, or a ConcatenatedFile object, which acts
    like a single file object, but magically combines multiple files."""
    # Fill in the array of file names
    filenames = [filename]

    READ = "r"
    READ_BINARY = "rb"

    N = 1
    while True:
        looking_for = filename + "_" + str(N)
        if os.path.exists(looking_for):
            filenames.append(looking_for)
            N += 1
        else:
            # No more files
            break

    if len(filenames) == 1:
        return open(filename, mode)
    else:
        if not mode in [READ, READ_BINARY]:
            raise PyAnnolibError("Only read-only mode is supported.")
        return concatfile.ConcatenatedFile(filenames, mode)
