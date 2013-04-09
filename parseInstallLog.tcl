#!/bin/sh
#exec tclsh "$0" "$@"

# parse EA install log files
#
# This program reads an install log, attempting to weed out all of the crap
#
# usage:
# tclsh parseInstallLog.tcl <logfile>
#


#---------------------------------------------------------------------
# parseFile
#
#       Read from the install log, printing out only the relevant
#    lines
#
# Results:
#       None.
#---------------------------------------------------------------------

proc parseFile {filename} {
    set lastlinefound false

    if {[catch {open $filename r} f]} {
      puts stdout "parselog: $f"
      exit 1
    }

    while {[gets $f line] != -1} {
        if {[string match {*\* This is build:*} $line]} {
            puts $line
         
        } elseif {[string match {*Read Previous Options File setting*} $line]} {
            puts $line
        } elseif {[ string match {*Executing action Copy File logfile to final location*} $line]} {
		   puts $line;set lastlinefound true
        } elseif {[string match {*<%EC_AGENT_AGENT_NUMBER%> greater <%EC_PROCESSOR_COUNT%>*} $line]} {
            puts $line
		 if {[gets $f line] != -1} { puts $line }

        } elseif {[string match {*Check*} $line]} {
        } elseif {[string match {*Installing*} $line]} {
        } elseif {[string match {*Skipping action*} $line]} {
        } elseif {[string match {*Executing*} $line]} {
        } elseif {[string match {*Call Finish*} $line]} {
        } elseif {[string match {*Copy*} $line]} {
        } elseif {[string match {*Rename*} $line]} {
        } elseif {[string match {*Error while executing*} $line]} {
            puts **********************>;puts $line;
        } elseif {[string match {*Building*} $line]} {
            puts $line
        } elseif {[string match {*WARNING*} $line]} {
            puts $line
        } elseif {[string match {*PATH=:*} $line]} {
            puts $line
        } elseif {[string match {*lofs*} $line]} {
            puts $line
        } elseif {[string match {*make*} $line]} {
            puts $line
        } elseif {[string match {*Wait For CM to Start*} $line]} {
            puts $line
        } elseif {[string match {*Create File Link*} $line]} {
            puts $line
        } elseif {[string match {*ERROR*} $line]} {
            puts $line
        } elseif {[string match {*\*\* Free Disk Size*} $line]} {
            puts $line
		 if {[gets $f line] != -1} { puts $line }
		 if {[gets $f line] != -1} { puts $line }
		 if {[gets $f line] != -1} { puts $line }
		 if {[gets $f line] != -1} { puts $line }
		 if {[gets $f line] != -1} { puts $line }

        } elseif {[string match {*Displaying pane*} $line]} {
            puts $line
        } elseif {[string match {*Setting active setup type to*} $line]} {
            puts $line
	  }
    }
    if {$lastlinefound == false} {
        puts stderr "The install log was abnormally terminated."
	}

puts "** END OF INSTALL LOG **"
}

# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------

proc main {} {

    # Must be given name of input file.

    set fname [lindex $::argv 0]
    if {$fname == ""} {
        puts stderr "Usage: parseInstallLog <logfile>"
        exit 1
    }
    puts "Parsing $fname\n"

    parseFile $fname
}
main
