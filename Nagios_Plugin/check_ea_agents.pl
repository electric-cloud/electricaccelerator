#!/usr/bin/perl -w
use strict;
use Getopt::Long;
use Date::Parse;
use XML::LibXML; 

sub print_help ();

my $PROGNAME="check_ea_agents";
my $PROGVER="1.0";

my ($opt_h, $opt_V);

Getopt::Long::Configure('bundling');
GetOptions(
  "V"   => \$opt_V, "version"	=> \$opt_V,
  "h"   => \$opt_h, "help"	=> \$opt_h);

if ($opt_V) {
  print "$PROGNAME $PROGVER\n";
  exit 0;
}

if ($opt_h) {
  print_help();
  exit 0;
}

#
#    <agent>
#      <agentId>1</agentId>
#      <agentKey>263786994</agentKey>
#      <agentName>wrc-s76-1</agentName>
#      <agentVersion>6.1.0.44495 64-bit (build_6.1_44495_OPT_2012.06.01_18:40:15)</agentVersion>
#      <efsVersion>6.1.0.44495 64-bit (build_6.1_44495_OPT_2012.06.01_18:39:07)</efsVersion>
#      <enabled>1</enabled>
#      <hostName>wrc-s76</hostName>
#      <lastPingTime>2012-10-13T00:40:49.596Z</lastPingTime>
#      <platform>linux</platform>
#      <status>1</status>
#      <statusDetail>Most recent heartbeat from Agent to CM failed. </statusDetail>
#      <inPenaltyBox>0</inPenaltyBox>
#    </agent>

my $total = 0;
my $dead = 0;
my $live = 0;
my $disabled = 0;
my $nohb = 0;

my $ctime = time() - 300;
my $lptime;

#my $login = `/opt/ecloud/i686_Linux/bin/cmtool --server=wrc-m1330 login admin changeme`;
my $login = `/opt/ecloud/i686_Linux/bin/cmtool --server=wrc-m1330 login nagios nagios`;
my $parser = XML::LibXML->new(); 
my $res = $parser->parse_string($login); 

if ("1" ne $res->findvalue('//response/@requestId')) {
  print "EA_AGENTS UNKNOWN Failed to connect to server\n";
  exit 3;
}


my $agentList = `/opt/ecloud/i686_Linux/bin/cmtool --server=wrc-m1330 getAgents`;
$parser = XML::LibXML->new(); 
$res = $parser->parse_string($agentList); 

if ("1" eq $res->findvalue('//response/@requestId')) {
  foreach my $agent ($res->findnodes('//agent')) { 
    $total = $total + 1;
    if ("1" ne $agent->findvalue('./enabled')) {
      $disabled = $disabled + 1;
    } else {
      if ("1" eq $agent->findvalue('./status')) {
        $live = $live + 1;
        my($lastPingTime) = $agent->findvalue('./lastPingTime'); 
        $lptime = str2time($lastPingTime);
        if ($lptime < $ctime) {
          $nohb = $nohb + 1;
        }
      } else {
        $dead = $dead + 1;
      }
    }
  } 
  if ((0 < $dead) or (0 < $nohb)) {
   print "EA_AGENTS CRITICAL | TOTAL=$total DISABLED=$disabled LIVE=$live DEAD=$dead NOHEARTBEAT=$nohb\n";
   exit 2;
  } else {
   print "EA_AGENTS OK | TOTAL=$total DISABLED=$disabled LIVE=$live DEAD=$dead NOHEARTBEAT=$nohb\n";
   exit 0;
  } 
} else {
  print "EA_AGENTS UNKNOWN  Failed to connect to server\n";
  exit 3;
}

sub print_help () {
  print "$PROGNAME $PROGVER\n";
  print "Copyright (c) 2013 Electric Cloud\n\n";
  print "Usage:\n";
  print "  $PROGNAME \n";
  print "  $PROGNAME [-h | --help]\n";
  print "  $PROGNAME [-V | --version]\n";
  print "\n";
}
