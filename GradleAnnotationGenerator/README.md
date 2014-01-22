## Gradle Build Analytics and Dependency Visualization 
The GradleAnnotationGenerator project is the data generation part of an interactive build and dependency visualization and analytics utility for [Gradle](http://www.gradle.org)-builds, based on [ElectricInsight](http://www.electric-cloud.com/products/electricaccelerator.php?tab=ei). This extends or complements the functionality provided by the existing Gradle [--profile](http://www.gradle.org/docs/current/userguide/tutorial_gradle_command_line.html#sec:profiling_build) and [HTML dependency report](http://forums.gradle.org/gradle/topics/add_an_html_dependency_report) features - enabling quick visual overview of build performance as well as ability for an engineer to really zoom in and dig deep in order to interactively understand structural behaviour and dependency relationships, allowing for troubleshooting and performance optimization at millisecond resolution.

Below is a sample output from this project - a screenshot of the parallel Gradle-build of Gradle itself where the Y-axis represents concurrent threads, the X-axis represents time and each box represents the workload (sections of a task or a test) as individual jobs. Jobs are categorized by type which is visualized by the colour-coding. More details in the example section [below](#examples):
![Visualization of the gradle Gradle build](http://bit.ly/Jbx1VG "Visualization of the gradle Gradle build")

## ElectricInsight
ElectricInsight is a powerful tool to visually depict the structure of a software build, down to the file level - empowering software and build engineers to easily pinpoint performance problems and conflicts in a build. The default usage of ElectricInsight is as an add-on to [ElectricAccelerator](http://www.electric-cloud.com/products/electricaccelerator.php), mining the information produced by ElectricAccelerator to provide an easy-to-understand, graphical representation of the build structure for performance analysis. It provides detailed information and reports on each parallel worker of the build infrastructure - for at-a-glance visualization, analytics and diagnostics. It can also predict and model how build times would be impacted by adding additional build infrastructure, to help guide hardware investment decisions.

## <a name="prerequisites"></a>Prerequisites
1. ElectricInsight, which comes bundled with the freely available [ElectricAccelerator Developer Edition](http://bit.ly/I4turK).
2. A gradle build running in your environment, or any of the [annotations from this repository](https://github.com/electriccommunity/electricaccelerator/tree/master/GradleAnnotationGenerator/annotations)

## Usage
1. Make sure you meet the [prerequisites](#prerequisites)
2. Retrieve the [Gradle init-script](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/initscript/init-generateanno.gradle) from this project
3. Add the --init-scipt/-I flag to load the [initialization script](http://www.gradle.org/docs/current/userguide/init_scripts.html) when running your gradle build:
   ```<command-to-run-your-regular-gradle-build> --init-script <path-to-GradleAnnotationGenerator-init-script> <gradle-tasks>```
4. Open gradle.anno (the generated Gradle annotation file) with ElectricInsight:
   ```einsight gradle.anno```
5. From here you can interactively explore the ElectricInsight reporting and analysis engine for your gradle build, see some example findings and use-cases [below](#examples).

If you lack a Gradle build environment but want to give this a try, go ahead and download some pre-existing annotation files [here](https://github.com/electriccommunity/electricaccelerator/tree/master/GradleAnnotationGenerator/annotations). 

##  <a name="examples"></a>Example Build Visualizations
While working on this project I have used four gradle builds as my testbed and benchmark - [gradle](#example_gradle), [hibernate-orm](#example_hibernate), [spring-framework](#example_spring) and [griffon](#example_griffon). Interestingly, they all exhibit different behaviours and constraints with different workload dominating the total time by type - test execution (gradle), code analysis (hibernate-orm), Javadoc generation (spring-framework) and Java compiles (griffon).

Below are further details and screenshots from my explorations. The following command-line were used for building all projects:

```
./gradlew --parallel --init-script <path-to-GradleAnnotationGenerator-init-script> clean build
```

### <a name="example_gradle"></a>gradle
The [gradle](https://github.com/gradle/gradle) build is interesting because the workload is heavily dominated by testing, which is forked and hence triggers a large amount of parallelization. Interestingly though, build time is not bounded by the test workload and we can easily spot the :docs:dslHtml as being the likely long pole. Using the Longest Serial Chain report we can also confirm that being the case, informing us it would be worthwhile to try and move the :docs project up earlier in the execution graph.

##### Workload Distribution:
![Visualization of the gradle gradle build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_gradle_anno.png?raw=true "Visualization of the gradle gradle build")

##### Job Time By type:
_Legend: "Library Link"=>"JUnit/TestNG",  "Noop"=>"Non-classified", "Miscellaneous"=>"Gradle Overhead", "Java Compile", "Compile"=>"Codenarc/Checkstyle/Findbugs", "Code gen"=>"Javadoc"_
![Job-time-by-type for the gradle gradle build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_gradle_JobTimeByType.png?raw=true "Job-time-by-type for the gradle gradle build")

##### Job Dependency Visualization:
ElectricInsight can visually highlight all dependent and waiting jobs from any given job, and allow for interactive traversal through the dependency/execution graph. Red emphasis in below screenshot indicates all waiting jobs from the "Graph Populated" job.
![Job dependency visualization for the gradle gradle build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_gradle_JobDependencyVisualization.png?raw=true "Job dependency visualization for the gradle gradle build")

##### Longest Serial Chain:
The Longest Serial Chain report is using dependency and runtime information to determine and visualize the chain of jobs included in the longest serial chain. Note that in this current implementation where there are no available dependency information between [Gradle TestDescriptor](http://www.gradle.org/docs/current/javadoc/org/gradle/api/tasks/testing/TestDescriptor.html) objects, all test suites and test cases within the suites are treated as non-dependent, hence parallelizable.
![Longest Serial Chain for the gradle gradle build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_gradle_LongestSerialChain.png?raw=true "Longest Serial Chain for the gradle gradle build")

##### ElectricSimulator:
The ElectricSimulator lets you visualize how the build time would change given a varying amount of build infrastructure.
![ElectricSimulator report for the gradle gradle build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_gradle_ElectricSimulator.png?raw=true "ElectricSimulator report for the gradle gradle build")

##### Quickly finding failed tasks/tests
During my testing I have built the [Gradle 1.9-rc-2 codebase](http://services.gradle.org/distributions/gradle-1.9-rc-2-src.zip) which was failing in my environment due to some gcc test problems. Clicking on the binoculars with a red cross gives a quick listing of all the failed tests:
![Failed jobs in the gradle gradle build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_gradle_FailedJobs.png?raw=true "Failed jobs in the gradle gradle build")

### <a name="example_hibernate"></a>hibernate-orm
The first half of the [hibernate-orm](https://github.com/hibernate/hibernate-orm) build is dominated by parallel FindBugs workload, while the later half flattens out into a string of serial test workload.

##### Workload Distribution:
![Visualization of the gradle hibernate-orm build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_hibernate-orm_anno.png?raw=true "Visualization of the gradle hibernate-orm build")

##### Job Time By type:
_Legend: "Library Link"=>"JUnit/TestNG",  "Noop"=>"Non-classified", "Miscellaneous"=>"Gradle Overhead", "Java Compile", "Compile"=>"Codenarc/Checkstyle/Findbugs", "Code gen"=>"Javadoc"_
![Job-time-by-type for the gradle hibernate-orm build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131106_hibernate-orm_JobTimeByType.png?raw=true "Job-time-by-type for the gradle hibernate-orm build")

##### Longest Serial Chain:
![Longest Serial Chain for the hibernate-orm gradle build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_hibernate-orm_LongestSerialChain.png?raw=true "Longest Serial Chain for the hibernate-orm gradle build")

##### ElectricSimulator:
![ElectricSimulator report for the hibernate-orm gradle build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_hibernate-orm_ElectricSimulator.png?raw=true "ElectricSimulator report for the hibernate-orm gradle build")

### <a name="example_spring"></a>spring-framework
The [spring-framework](https://github.com/spring-projects/spring-framework) build is dominated by parallel javadocs workload, where one of those jobs happens to fail in my environment.

##### Workload Distribution:
![Visualization of the gradle spring-framework build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_spring-framework_anno.png?raw=true "Visualization of the gradle spring-framework build")

##### Job Time By type:
_Legend: "Library Link"=>"JUnit/TestNG",  "Noop"=>"Non-classified", "Miscellaneous"=>"Gradle Overhead", "Java Compile", "Compile"=>"Codenarc/Checkstyle/Findbugs", "Code gen"=>"Javadoc"_
![Job-time-by-type for the gradle spring-framework build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_spring-framework_JobTimeByType.png?raw=true "Job-time-by-type for the gradle spring-framework build")

##### Quickly finding reasons for failed tasks/tests
Let's use ElectricInsight to find out more about the failing javadoc-job. Clicking on the binoculars with a red cross gives a quick listing of all the failed tests, then clicking on that top job brings up a view with further details where I can see e.g. start/end-time, thread and also the exception that triggered the failure. 
![Failed job details](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131106_spring-framework_FailedJobException.png?raw=true "Failed job details")

##### Quick access to a lot of details of tasks/tests
Moving on to the Annotation tab gives even more details such as e.g. the job output and also all the read/written files.
![Failed job output and read/written files](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131106_spring-framework_FailedJobOutputOpList.png?raw=true "Failed job output and read/written files")

### <a name="example_griffon"></a>Griffon
The [griffon](https://github.com/griffon/griffon) build is dominated by Java/Groovy compile time and codenarc analysis workload. It's a short build but still has quite a bit of serialization, so it seems could still be further shortened by more aggressive parallelization.

##### Workload Distribution:
![Visualization of the gradle griffon build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_griffon_anno.png?raw=true "Visualization of the gradle griffon build")

##### Job Time By type:
_Legend: "Library Link"=>"JUnit/TestNG",  "Noop"=>"Non-classified", "Miscellaneous"=>"Gradle Overhead", "Java Compile", "Compile"=>"Codenarc/Checkstyle/Findbugs", "Code gen"=>"Javadoc"_
![Job-time-by-type for the gradle griffon build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131120_griffon_JobTimeByType.png?raw=true "Job-time-by-type for the gradle griffon build")

## Next Steps
I think this project may be pretty useful as-is (it was certainly useful for me as a project to learn more about Gradle! :-)), but there are obviously a number of interesting extensions/improvements that could be considered fur the future. Off the top of my head, here are some:

1. Thread Allocation

   Rather than relying on a custom algorithm for determining which thread a particular job is running on (which turned out to be fairly complex, and by no means is perfect), explore extending the Gradle [Task](http://www.gradle.org/docs/current/javadoc/org/gradle/api/Task.html)/[Test](http://www.gradle.org/docs/current/javadoc/org/gradle/api/tasks/testing/TestDescriptor.html) API's with information about which worker/thread is currently in use. This would yield a _true_ representation of how the workload is scheduled and allocated on the build infrastructure. 

2. Capturing stdout/stderr per job

   It seems Gradle has no current ability to capture stdout/stderr per task/test, at least not that I've been able to figure out. If you register an outputlistener of some kind, *all* output at the specified loglevel will be captured regardless of origin. It would obviously be very beneficial to have capability to separate and identify source of the output.

3. Live monitoring

   ElectricInsight supports live monitoring of builds. Rather than write data to file it would not be too complex to write it to a socket connected to ElectricInsight. This would allow one to look at this project as a real time build monitor as well as a post-build analysis utility.

4. Custom job categorization

   It would be a nice feature to have ability to customize ElectricInsight job categorization.

5. Improve flexibility of usage, e.g. by allowing for custom generated annotation-files and for varying amount of annotation detail.

## Problems? / Issues? / Feedback?
Please take note this proejct is not commercially supported by Electric Cloud. Any issues or problems are best discussed at http://ask.electric-cloud.com or by contacting me directly on [email](mailto:drosen@electric-cloud.com)/[twitter](https://twitter.com/adr0sen).
Contributions are very welcome - please let me know if you have an interest to help.

Lastly, I'm very interested in hearing your feedback!
Email: drosen@electric-cloud.com
Twitter: [@adr0sen](https://twitter.com/adr0sen)


