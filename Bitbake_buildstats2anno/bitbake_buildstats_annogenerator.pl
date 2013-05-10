#!/usr/bin/perl
###
# bitbake_buildstats_annogenerator - based on buildstats output from a bitbake build, generate ElectricInsight compatible annotation data
#
# Usage:
#	./<path-to-this-script> <path-to-bitbake-build-stats> <anno-outfile>
#		Defaults:
#			path-to-bitbake-build-stats: 	cwd
#			anno-outfile:					./bitbake_anno.xml
#
###

use strict ;
use warnings ;
use POSIX;
use Cwd;
use File::Basename;
use List::Util qw(first max maxstr min minstr reduce shuffle sum);
use IO::Uncompress::Gunzip qw(gunzip $GunzipError) ;

my $bitbake_buildstats = ".";
my $outfile = "./bitbake_anno.xml";
if($ARGV[0]){
	$bitbake_buildstats = $ARGV[0];
}
if($ARGV[1]){
	$outfile = $ARGV[1];
}

my %annotasks = ();
my $normalizer = LONG_MAX;

# This is a mapping to enable generation of different ElectricInsight job-categories, for e.g. color-coding and reporting purposes 
my %jobtype_mapping = (
	do_compile 					=> {type => "rule", namesuffix => "   .o"},
	do_configure				=> {type => "end"},
	do_fetch 					=> {type => "rule"},
	do_install 					=> {type => "rule", cmd => "touch"},
	do_package 					=> {type => "rule", cmd => "ld"},
	do_package_write_rpm 		=> {type => "exist"},
	do_packagedata 				=> {type => "remake"},
	do_patch 					=> {type => "rerun"},
	do_populate_lic 			=> {type => "rule"},
	do_populate_sysroot 		=> {type => "rule", cmd => "bison"},
	do_rm_work 					=> {type => "rule", status => "skipped"},
	do_unpack 					=> {type => "rule", namesuffix => "   .a"},
	do_kernel_checkout			=> {type => "rule"},
	do_validate_branches		=> {type => "rule"},
	do_kernel_configme			=> {type => "rule"},
	do_install_locale			=> {type => "rule"},
	do_evacuate_scripts			=> {type => "rule"},
	do_generate_toolchain_file	=> {type => "rule"},
	do_configure_ptest_base		=> {type => "rule"},
);

my %thread_end_mapping;
# initialize at least one thread
for(my $i=0; $i<1; $i++){
	$thread_end_mapping{$i} = 0.0;
}

analyze_dir($bitbake_buildstats);
print "\nGenerating annotation from bitbake buildstats at $bitbake_buildstats into $outfile...\n";
open FILE, ">$outfile" or die $!;

# Add some generic preamble data to annotation - should not be significant
print FILE '<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE build SYSTEM "build.dtd">
<build id="'.int(rand(10000)).'" cm="192.168.27.10:8030" start="Tue 16 Apr 2013 05:08:54 PM CEST">
<make level="0" cmd="emake -f waba0810.mkf --emake-cm=192.168.27.10 --emake-maxagents=1 --emake-annodetail=file,waiting,history,env --emake-annofile=emake-anno-@ECLOUD_BUILD_ID@.xml --emake-debug=jnfgh --emake-logfile=emake-debug-@ECLOUD_BUILD_ID@.log" cwd="/opt/ecloud/spiroot/a1/source" mode="gmake3.81">';
foreach my $value (sort {$annotasks{$a}{Started} <=> $annotasks{$b}{Started} } keys %annotasks)
{
	# normalize start and end timings
	my $start = $annotasks{$value}{Started}-$normalizer;
	my $end = $annotasks{$value}{Ended}-$normalizer;
	my $jobtype = ($jobtype_mapping{$annotasks{$value}{Task}}{type})?($jobtype_mapping{$annotasks{$value}{Task}}{type}):("rule");
	my $jobstatus = ($jobtype_mapping{$annotasks{$value}{Task}}{status})?("status=\"".$jobtype_mapping{$annotasks{$value}{Task}}{status}."\""):("");
	my $jobcmd = ($jobtype_mapping{$annotasks{$value}{Task}}{cmd})?("<command line=\"1\">\n<argv>".$jobtype_mapping{$annotasks{$value}{Task}}{cmd}."</argv>\n</command>\n"):("");
	my $jobname = $value;
	#$jobname .= ($annotasks{$value}{Task} eq "do_compile")?"   .o":"";
	$jobname .= ($jobtype_mapping{$annotasks{$value}{Task}}{namesuffix})?$jobtype_mapping{$annotasks{$value}{Task}}{namesuffix}:"";
	my $jobid = int(rand(LONG_MAX));
	
	#determine which thread we're running on
	my $thread = 0;
	my $thread_end = 0.0;
	my $i = -1;
	foreach my $key (sort {$thread_end_mapping{$a} <=> $thread_end_mapping{$b} } keys %thread_end_mapping)
	{
		if($start > $thread_end_mapping{$key}){
			#print "$key: $start $end $thread_end_mapping{$key}\n";
			$i = $key;
			last;
		}
	}
	if($i == -1){
		$i = keys(%thread_end_mapping);
	}
	$thread_end_mapping{$i} = $end;	
	
	# generate job-xml
	my $xml = "<job id=\"$jobid\" thread=\"f5a83b90\" $jobstatus type=\"$jobtype\" name=\"$jobname\">\n";
	$xml .= $jobcmd;
	$xml .= "<timing invoked=\"".sprintf("%.6f", $start)."\" completed=\"".sprintf("%.6f", $end)."\" node=\"bb-thread-$i\"/>\n";
	$xml .= "</job>\n";
	
	#print $xml;
	print FILE $xml;
}
print FILE '</make>
</build>';
close FILE;

sub analyze_dir{
	my $dirname = $_[0];

	opendir(DIR, $dirname) or die "can't opendir $dirname: $!";
	my @files=readdir(DIR);
	my @files_to_use=sort(@files);

	foreach (@files_to_use) {
		my $file = $_;
		if($file =~ m/^[.]/){
			next;
		}
		if(-d "$dirname/$file"){
			#print "Dir: $dirname/$file\n";		
			analyze_dir("$dirname/$file");
		}
		else{
			#print "$dirname/$file\n";
			if("$dirname/$file" =~ m/^[.]$/){
				next;
			}
			my $basename = basename($dirname);
			#print "$basename\n";
			open FILE, "$dirname/$file" or die $!;
			my $started = 0.0;
			my $ended = 0.0;
			my $cpu_usage = 0.0;
			
			while (<FILE>) {
				if($_ =~ m/^[#]/){
					next;
				}
				if($_ =~ m/^Started: ([-+]?[0-9]*\.?[0-9]+)/){
					#print "$basename:$file $1\n";
					$started = $1;
					$normalizer = min($started, $normalizer);
				}
				if($_ =~ m/^Ended: ([-+]?[0-9]*\.?[0-9]+)/){
					$ended = $1;
				}
				if($_ =~ m/^CPU usage: ([-+]?[0-9]*\.?[0-9]+)/){
					$cpu_usage = $1;
				}
			}
			if($started != 0.0){				
				$annotasks{$basename.":".$file}{Started} = $started;
				$annotasks{$basename.":".$file}{Ended} = $ended;
				$annotasks{$basename.":".$file}{CPU_Usage} = $cpu_usage;
				$annotasks{$basename.":".$file}{Task} = $file;
			}
		}
	}
}


