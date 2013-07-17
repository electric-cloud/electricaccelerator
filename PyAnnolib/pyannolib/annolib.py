"""
Handle the emake annotation file.
"""

import xml.sax
import types

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

class FinishedHeaderException(Exception):
    """This is used internally for AnnoXMLHeaderHandler to
    stop processing the XML file mid-stream and resume executing
    back where it was called (in parseFH)."""
    pass

class AnnotatedBuild:
    ID = "id"
    CM = "cm"
    START = "start"

    def __init__(self, filename, fh=None):
        """Can raise IOError"""
        # Initialize this since it is used in __str
        self.build_id = None

        # This is initialized now, but won't be read until
        # the very end of the file.
        self.metrics = {}

        if filename:
            assert not fh, "filename and fh both given"

            # Allow the exception to go back to the caller of AnnoFileParser
            self.fh = open(filename)

        elif fh:
            self.fh = fh

        else:
            assert 0, "Neither filename or fh given"

        # Do the parse
        self._parseFH()

    def close(self):
        """Closes the filehandle, which may be needed if you had
        AnnotatedBuild open() it for you."""
        assert self.fh, "fh has no value"
        self.fh.close()

    def __str__(self):
        return "<AnnotatedBuild id=%s>" % (self.build_id,)

    def _parseFH(self):
        """Parse the annotation file handle"""

        # Create the parser
        parser = xml.sax.make_parser()

        # Create the handler
        handler = AnnoXMLHeaderHandler()

        # Tell the parser to use our handler
        parser.setContentHandler(handler)

        # Don't fetch the DTD
        parser.setFeature(xml.sax.handler.feature_external_ges, False)

        # Parse the file
        try:
            parser.parse(self.fh)
        except FinishedHeaderException, exc:
            # After parsing the header, it throws an exception
            # so we can regain control here. We reset the file handle
            # and return the Build object to the user. The Build
            # object has it's own parse_jobs() function, which will
            # re-parse the annotation file, looking only at the "body"
            # of the file, not the "header".

            # The hdr_data tuple is the first argument to the exception,
            # which is what we need to store before we can parse
            # the jobs sequentially.
            hdr_data = exc.args[0]
            self._init_from_hdr_data(hdr_data)

            # Set the filehandle back to the beginning; when parseJobs()
            # is run, it uses AnnoXMLBodyHandler, which skips over all the XML
            # fields that are part of the header. It's not the most efficient
            # way to handle the separation of body and header; it would be
            # much nicer to skip over the header and start parsing where
            # the body starts, but the innards of xml.sax are complicated,
            # and the header itself is rather small when compared to the
            # body, so it's not a horrible solution.
            SEEK_BEGINNING = 0
            self.fh.seek(SEEK_BEGINNING)

            # Done with processing the header, so return now.
            return

        # Because we caught FinishedHeaderException to return
        # the Build object to the user, we should not have
        # reached this point.
        raise ValueError("Should not have reached. Corrupt Build record.")


    def _init_from_hdr_data(self, hdr_data):
        """Use the header data to populte our data structures."""
        (xmlattrs, properties, vars) = hdr_data
        self.build_id = xmlattrs[self.ID]
        self.cm = xmlattrs[self.CM]
        self.start_text = xmlattrs[self.START]

        self.properties = properties
        self.vars = vars

    def setMetrics(self, metrics):
        """This is called by the body parser because metrics
        come at the very end of the annotation file."""
        self.metrics = metrics

    def getCM(self):
        return self.cm

    def getStart(self):
        return self.start_text

    def getBuildID(self):
        return self.build_id

    def getProperties(self):
        return self.properties

    def getVars(self):
        return self.vars

    def getMetrics(self):
        return self.metrics

    def parseJobs(self, cb):
        """Parse jobs and call the callback for each Job object."""
        if not self.fh:
            raise ValueError("filehandle was not set in Build object")

        # Create the parser
        parser = xml.sax.make_parser()

        # Create the handler
        handler = AnnoXMLBodyHandler(self, cb)

        # Tell the parser to use our handler
        parser.setContentHandler(handler)

        # Don't fetch the DTD
        parser.setFeature(xml.sax.handler.feature_external_ges, False)

        # Parse the file
        parser.parse(self.fh)

        # I thought I needed to close the parser here
        # with parser.close(), but it's throwing an exception.
        # I'm starting to think I don't need to call this.
        #parser.close()

    def getAllJobs(self):
        """Gather all Job records in a list and return that list.
        It's a convenience function; the same could be done via parseJobs()
        and the appropriate callback."""
        jobs = []

        def job_cb(job):
            jobs.append(job)

        self.parseJobs(job_cb)

        return jobs

###################################################

class AnnoXMLNames:
    """These constants are used by both AnnoXMLHeaderHandler,
    and AnnoXMLBodyHandler, but don't need to be global. So, they
    are in this base class, inherited by the two using classes."""
    # Found in the "header"
    ELEMENT_BUILD = "build"
    ELEMENT_PROPERTIES = "properties"
    ELEMENT_PROPERTY = "property"
    ELEMENT_ENVIRONMENT = "environment"
    ELEMENT_VAR = "var"

    # These attributes are handled by the AnnoXMLHeaderHandler directly
    ATTR_PROP_NAME = "name"
    ATTR_VAR_NAME = "name"

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

    # These attributes are handled by the AnnoXMLBodyHandler directly
    ATTR_WAITINGJOBS_IDLIST = "idList"
    ATTR_METRIC_NAME = "name"
    ATTR_OUTPUT_SRC = "src"
    ATTR_FAILED_CODE = "code"

########################

class AnnoXMLHeaderHandler(xml.sax.handler.ContentHandler, AnnoXMLNames):
    """This sax parser handles the "header" portion of the annotation
    XML file, before the build jobs start."""
    def __init__(self):
        self.chars = ""
        self.property_name = None
        self.var_name = None
        self.indent = 0

        self.build_xmlattrs = None
        self.properties = {}
        self.vars = {}

    def startElement(self, name, xmlattrs):
        self.chars = ""

        if name == self.ELEMENT_BUILD:
            self.build_xmlattrs = xmlattrs

        elif name == self.ELEMENT_PROPERTIES:
            pass

        elif name == self.ELEMENT_PROPERTY:
            self.property_name = xmlattrs[self.ATTR_PROP_NAME]

        elif name == self.ELEMENT_ENVIRONMENT:
            pass

        elif name == self.ELEMENT_VAR:
            self.var_name = xmlattrs[self.ATTR_VAR_NAME]



    def endElement(self, name):
        if name == self.ELEMENT_PROPERTY:
            self.properties[self.property_name] = self.chars
            self.property_name = None

        elif name == self.ELEMENT_VAR:
            self.vars[self.var_name] = self.chars
            self.var_name = None

        # at the end if <environment> we can pass back
        # the header fields
        elif name  == self.ELEMENT_ENVIRONMENT:
            hdr_data = (self.build_xmlattrs, self.properties, self.vars)
            raise FinishedHeaderException(hdr_data)

        self.chars = ""


    def characters(self, chars):
        self.chars += chars



####################################################

        


class MakeProcess:

    LEVEL = "level"
    CMD = "cmd"
    CWD = "cwd"
    OWD = "owd"
    MODE = "mode"

    def __init__(self, xmlattrs):
        self.level = xmlattrs[self.LEVEL]
        self.cmd = xmlattrs[self.CMD]
        self.cwd = xmlattrs[self.CWD]
        self.owd = xmlattrs.get(self.OWD) # implied, not required
        self.mode = xmlattrs[self.MODE]

    def __str__(self):
        return "<MakeProcess level=%s cwd=%s>" % (self.level, self.cwd)

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

class Job:

    ID = "id"
    STATUS  ="status"
    THREAD = "thread"
    TYPE = "type"
    SUCCESS = 0

    def __init__(self, xmlattrs):
        self.job_id = xmlattrs[self.ID]
        self.status = xmlattrs.get(self.STATUS, JOB_STATUS_NORMAL)
        self.thread = xmlattrs[self.THREAD]
        self.type = xmlattrs[self.TYPE]
        self.output = None
        self.make = None
        self.timing = None
        self.oplist = []
        self.waiting_jobs = []
        self.commands = []
        self.deplist = []
        self.conflict = None

        # The return value of the Job. By default
        # we assume success, but a <failed> record overrides that.
        self.retval = self.SUCCESS

    def __str__(self):
        return "<Job id=%s>" % (self.job_id,)

    def setOutput(self, output):
        self.output = output

    def setOpList(self, op_elements):
        self.oplist = op_elements

    def setMakeProcess(self, make_elem):
        self.make = make_elem

    def setTiming(self, timing):
        self.timing = timing

    def setWaitingJobs(self, ids_string):
        # The job IDs are space-delimited in the string;
        # use split() to create a list
        self.waiting_jobs = ids_string.split()

    def addCommand(self, cmd):
        assert isinstance(cmd, Command)
        self.commands.append(cmd)

    def addDep(self, dep):
        self.deplist.append(dep)

    def setRetval(self, new_value):
        self.retval = new_value

    def setConflict(self, conflict):
        self.conflict = conflict

    def getID(self):
        return self.job_id

    def getStatus(self):
        return self.status

    def getThread(self):
        return self.thread

    def getType(self):
        return self.type

    def getOutput(self):
        return self.output

    def getOperations(self):
        return self.oplist

    def getMakeProcess(self):
        return self.make

    def getTiming(self):
        return self.timing

    def getWaitingJobs(self):
        return self.waiting_jobs

    def getCommands(self):
        return self.commands

    def getDependencies(self):
        return self.deplist

    def getRetval(self):
        return self.retval

    def getConflict(self):
        return self.conflict

class Operation:
    TYPE = "type"
    FILE = "file"
    FILETYPE = "filetype"
    FOUND = "found"
    ISDIR = "isdir"

    def __init__(self, xmlattrs):
        self.type = xmlattrs[self.TYPE]
        self.file = xmlattrs[self.FILE]
        self.filetype = xmlattrs.get(self.FILETYPE, OP_FILETYPE_FILE)
        self.found = xmlattrs.get(self.FOUND, OP_FOUND_TRUE)
        self.isdir = xmlattrs.get(self.ISDIR, OP_ISDIR_TRUE)

    def getType(self):
        return self.type

    def getFile(self):
        return self.file

    def getFileType(self):
        return self.filetype

    def getFound(self):
        return self.found

class Timing:
    INVOKED = "invoked"
    COMPLETED = "completed"
    NODE = "node"

    def __init__(self, xmlattrs):
        self.invoked = xmlattrs[self.INVOKED]
        self.completed = xmlattrs[self.COMPLETED]
        self.node = xmlattrs[self.NODE]

    def getInvoked(self):
        return self.invoked

    def getCompleted(self):
        return self.completed

    def getNode(self):
        return self.node

class Command:
    LINE = "line"

    def __init__(self, xmlattrs):
        # "line" is optional
        self.line = xmlattrs.get(self.LINE)
        self.argv = ""
        self.output = ""
        self.output_src = None

    def setArgv(self, text):
        self.argv = text

    def setOutput(self, text):
        self.output = text

    def setOutputSrc(self, text):
        self.output_src = text

    def getLine(self):
        return self.line

    def getArgv(self):
        return self.argv

    def getOutput(self):
        return self.output

    def getOutputSrc(self):
        return self.output_src

class Dependency:
    WRITE_JOB = "writejob"
    FILE = "file"
    TYPE = "type"

    def __init__(self, xmlattrs):
        self.write_job = xmlattrs[self.WRITE_JOB]
        self.file = xmlattrs[self.FILE]
        self.type = xmlattrs.get(self.TYPE, DEP_TYPE_FILE)

    def getWriteJob(self):
        return self.write_job

    def getFile(self):
        return self.file

    def getType(self):
        return self.type

class Conflict:
    TYPE = "type"
    WRITE_JOB = "writejob"
    FILE = "file"
    RERUN_BY = "rerunby"

    def __init__(self, xmlattrs):
        self.type = xmlattrs[self.TYPE]
        self.write_job = xmlattrs.get(self.WRITE_JOB)
        self.file = xmlattrs.get(self.FILE)
        self.rerun_by = xmlattrs[self.RERUN_BY]

    def getType(self):
        return self.type

    def getWriteJob(self):
        return self.write_job

    def getFile(self):
        return self.file

    def getRerunBy(self):
        return self.rerun_by


class AnnoXMLBodyHandler(xml.sax.handler.ContentHandler, AnnoXMLNames):
    """This sax parser handles the "body" portion of the annotation
    XML file, where the build jobs start."""

    def __init__(self, build, cb):
        self.build = build
        self.cb = cb
        self.chars = ""
        self.indent = 0

        # In local mode builds, make elements can nest,
        # so this list of make_elem's is a stack.
        self.make_elem = []
        self.job_elem = None
        self.output_text = None
        self.op_elements = None

        self.metrics = None
        self.metric_name = None

        self.command = None

    def startElement(self, name, xmlattrs):
#        spaces = self.indent * " "
#        print "%s<%s>" % (spaces, name)
#        self.indent += 1

        self.chars = ""

        if name == self.ELEMENT_MAKE:
            make_elem = MakeProcess(xmlattrs)
            self.make_elem.append(make_elem)
#            print make_elem

        elif name == self.ELEMENT_JOB:
            self.job_elem = Job(xmlattrs)
#            print self.job_elem

        elif name == self.ELEMENT_OUTPUT:
            self.output_text = ""

        elif name == self.ELEMENT_OPLIST:
            self.op_elements = []

        elif name == self.ELEMENT_OP:
            op_elem = Operation(xmlattrs)
            self.op_elements.append(op_elem)

        elif name == self.ELEMENT_METRICS:
            self.metrics = {}

        elif name == self.ELEMENT_METRIC:
            self.metric_name = xmlattrs[self.ATTR_METRIC_NAME]

        elif name == self.ELEMENT_WAITING_JOBS:
            ids_string = xmlattrs[self.ATTR_WAITINGJOBS_IDLIST]
            self.job_elem.setWaitingJobs(ids_string)

        elif name == self.ELEMENT_TIMING:
            timing = Timing(xmlattrs)
            self.job_elem.setTiming(timing)

        elif name == self.ELEMENT_COMMAND:
            self.command = Command(xmlattrs)
            self.job_elem.addCommand(self.command)

        elif name == self.ELEMENT_OUTPUT:
            assert self.command
            if xmlattrs.has_key(self.ATTR_OUTPUT_SRC):
                output_src = xmlattrs.get(self.ATTR_OUTPUT_SRC, OUTPUT_SRC_MAKE)
                self.command.setOutputSrc(output_src)

        elif name == self.ELEMENT_CONFLICT:
            conflict = Conflict(xmlattrs)
            self.job_elem.setConflict(conflict)

        elif name == self.ELEMENT_DEP:
            dep = Dependency(xmlattrs)
            self.job_elem.addDep(dep)

        elif name == self.ELEMENT_FAILED:
            code_text = xmlattrs[self.ATTR_FAILED_CODE]
            code_int = int(code_text)
            self.job_elem.setRetval(code_int)


        elif name in [
                self.ELEMENT_BUILD,
                self.ELEMENT_PROPERTIES,
                self.ELEMENT_PROPERTY,
                self.ELEMENT_ENVIRONMENT,
                self.ELEMENT_VAR,
                self.ELEMENT_ARGV,
                self.ELEMENT_DEPLIST,
                ]:
            pass

        else:
            assert 0, "Unhandled element: " + name

    def endElement(self, name):
#        spaces = self.indent * " "
#        print "%s</%s>" % (spaces, name)
#        self.indent -= 1

        if name == self.ELEMENT_MAKE:
            assert len(self.make_elem) > 0
            self.make_elem.pop()

        elif name == self.ELEMENT_OUTPUT:
            self.output_text = self.chars

        elif name == self.ELEMENT_JOB:
            assert len(self.make_elem) > 0
            self.job_elem.setOutput(self.output_text)

            # We are somewhat rigrous here. We could initialize
            # op_elements to [] at the beginning of a Job,
            # but instead, we only initialize it when we see an OpList.
            # So, only add that list to the Job object if it is a list.
            # If it was never initialized (op_elements == None),
            # then don't add it to the Job object.
            if type(self.op_elements) == types.ListType:
                self.job_elem.setOpList(self.op_elements)

            self.job_elem.setMakeProcess(self.make_elem[-1])

            self.cb(self.job_elem)

            self.job_elem = None
            self.output_text = None
            self.op_elements = None

        elif name == self.ELEMENT_METRIC:
            self.metrics[self.metric_name] = self.chars
            self.metric_name = None

        elif name == self.ELEMENT_METRICS:
            self.build.setMetrics(self.metrics)

        elif name == self.ELEMENT_TIMING:
            pass

        elif name == self.ELEMENT_ARGV:
            assert self.command
            self.command.setArgv(self.chars)

        elif name == self.ELEMENT_OUTPUT:
            assert self.command
            self.command.setOutput(self.chars)

        elif name == self.ELEMENT_COMMAND:
            assert self.command
            self.command = None

        self.chars = ""


    def characters(self, chars):
        self.chars += chars

