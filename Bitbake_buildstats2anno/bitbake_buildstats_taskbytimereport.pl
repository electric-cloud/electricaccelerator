use strict ;
use warnings ;
use Cwd;
use File::Basename;
use IO::Uncompress::Gunzip qw(gunzip $GunzipError) ;

my $basecwd = basename(getcwd);
if($basecwd eq "all"){
    $basecwd = "";
}

my %tasks = ();
my %configure = ();
my %package = ();
my %install = ();
my %clientipcount = ();
my %refcount = ();
my %uacount = ();
my %datecount = ();

my %count = (
	do_compile 				=> 0,
	do_configure			=> 0,
	do_fetch 				=> 0,
	do_install 				=> 0,
	do_package 				=> 0,
	do_package_write_rpm 	=> 0,
	do_packagedata 			=> 0,
	do_patch 				=> 0,
	do_populate_lic 		=> 0,
	do_populate_sysroot 	=> 0,
	do_rm_work 				=> 0,
	do_unpack 				=> 0,
);

my %elapsed_time = (
	do_compile 				=> 0,
	do_configure			=> 0,
	do_fetch 				=> 0,
	do_install 				=> 0,
	do_package 				=> 0,
	do_package_write_rpm 	=> 0,
	do_packagedata 			=> 0,
	do_patch 				=> 0,
	do_populate_lic 		=> 0,
	do_populate_sysroot 	=> 0,
	do_rm_work 				=> 0,
	do_unpack 				=> 0,
);

my %cpu_usage = (
	do_compile 				=> 0,
	do_configure			=> 0,
	do_fetch 				=> 0,
	do_install 				=> 0,
	do_package 				=> 0,
	do_package_write_rpm 	=> 0,
	do_packagedata 			=> 0,
	do_patch 				=> 0,
	do_populate_lic 		=> 0,
	do_populate_sysroot 	=> 0,
	do_rm_work 				=> 0,
	do_unpack 				=> 0,
);

analyze_dir(".");

print "\nJob time by type:\n";
my $totalsum = 0.0;
while ( my ($key, $value) = each(%elapsed_time) ) {
  $totalsum += $value;
}
while ( my ($key, $value) = each(%elapsed_time) ) {
	print "  $key => ".sprintf("%.1f", $value)."s (".sprintf("%.1f%%", 100*($value/($totalsum))).")\n";
}
print "\nTasks:\n";
while ( my ($key, $value) = each(%tasks) ) {
	print "$key: \n";
	#while ( my ($key2, $value2) = each(%$value) ) {
	#  print "  $key2 => $value2 \n";
	#}
	my $i=0;
	foreach my $value2 (sort {$$value{$b} <=> $$value{$a} } keys %$value)
	  {
	    if($i++ < 10){
	      print "   $value2 $$value{$value2}\n";
	    }
	  }

#	print for sort{ $b <=> $a } %$value;
#	foreach my $k (sort { $a <=> $b} keys %hash) {
#	  print $hash{$k} . " = " . $k . "\n";
#	}
}

#while ( ($family, $roles) = each %HoH ) {
#    print "$family: ";
#    while ( ($role, $person) = each %$roles ) {
#        print "$role=$person ";
#    }
#    print "\n";
#}

sub analyze_dir
{
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
			while (<FILE>) {
			  if($_ =~ m/^[#]/){
				next;
			      }
			  if($_ =~ m/^$basename: $file: Elapsed time: ([-+]?[0-9]*\.?[0-9]+) seconds/){
				$count{$file}++;
				$elapsed_time{$file} += $1;
				$tasks{$file}{$basename} = $1;
			      }
			}
		      }
	      }
      }


