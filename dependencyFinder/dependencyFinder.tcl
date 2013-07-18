#!/bin/sh
# restart -*-Tcl-*- \
exec tclsh "$0" "$@"

# Copyright (c) 2008 Electric Cloud, Inc.
# All rights reserved.

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

