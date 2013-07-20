#!/bin/sh
# restart -*-Tcl-*- \
exec tclsh "$0" "$@"

# Copyright (c) 2013, Adeel Malik
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

package require cmdline
load annolib.so

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

set PARAMS {
}


# ----------------------------------------------------------------------------
# PROCEDURE: getFilesReadByJob
# ARGUMENTS: jobId, indent
# ----------------------------------------------------------------------------

proc getFilesReadByJob {jobId indent} {
	global g filesList fileCount
	set jobOperations [$g(anno) job operations $jobId]
	foreach eachJobOperation $jobOperations {
		foreach {job op fname} $eachJobOperation {break}
		if {$op == "read" && [lsearch $filesList $fname] == -1} {
			# fetch filename from the entry
			set readFile [lindex $eachJobOperation 2]
			lappend filesList $readFile
			puts [format "%s%s" [string repeat " " $indent] $readFile]
#			puts "$jobId read $readFile"
			# 3. Find the jobs that wrote those files. [$anno file operations] again.
			getJobsThatCreateFile $readFile [expr $indent+2]
		}
	}	
}

# ----------------------------------------------------------------------------
# PROCEDURE: getJobsThatCreateFile
# ARGUMENTS: targetFile, indent
# ----------------------------------------------------------------------------

proc getJobsThatCreateFile {target indent} {
	global g jobsList
	set operations [$g(anno) file operations $target]
	foreach eachFileOperation $operations {
		foreach {job op fname} $eachFileOperation {break}
		if {$op == "create" } {
			lappend jobsList $job
#			set spacer [string repeat " " $indent]
#			puts [format "%s%s"  [string repeat " " $indent] $job]
#			puts "$target created by $job"
			# 2. Find the files read by that job. [$anno job operations] will help.
			getFilesReadByJob $job [expr $indent+2]
		}	
	}
}

proc main {} {
	global argv g jobsList filesList fileCount

    	# Build up the usage string.
    	set usage "\[options] <annofile> <filename>\n"
    	append usage " annofile            \
                   Name of annotation file.\n"
    	append usage " fname               \
                   Name of file to search for.\n\n"
    	append usage "options:"

	# Parse command line options.
	if {[catch {cmdline::typedGetoptions argv $::PARAMS $usage} result]} { 
	puts stderr $argv
	puts stderr $result
	exit 1
	}
	array set opt $result

	# First argument is the annotation file.

	set annofile [lindex $argv 0]
	set target [lindex $argv 1]

	# Whine if it is empty.

	if {$annofile == ""} {
	puts stderr "Usage: depinfo \[options\] <annofile>"
	exit 1
	}

	puts "*************** INPUTS ****************************"
	puts "Annotation file:      $annofile"
	puts "Target file    :      $target" 
	puts "***************************************************"

	# Open the annotation file and parse it.
	if {[catch {open $annofile r} fd]} {
		puts stderr "depinfo: error opening \"$annofile\": $fd"
		exit 1
	}	
	set g(anno) [anno create]
	$g(anno) load [open $annofile]
	set filesList {}
	set tab 0

	# 1. Find the job(s) that wrote the file. [$anno file operations] is a good starting point.
	puts "$target"
	getJobsThatCreateFile $target $tab
	puts "*****************************************************************"
	puts "There are [llength $filesList] files that directly or indirectly"
	puts "serve as input to make \"$target\" file."
	puts "*****************************************************************"

}

main

