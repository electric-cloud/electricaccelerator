# WORK IN PROGRESS - contact drosen@electric-cloud.com for any questions

# Gradle Build Visualization
* Do you want to have better insight into what your Gradle build is doing, and when? 
* Are you exploring the incubating parallel feature of Gradle and want to understand how well it is performing? 
* Are you a Gradle plugin developer and want a better understanding on how your plugin performs when integrated into your Gradle builds? 

This GradleAnnotationGenerator project is the data generation part of an interactive build visulization utility for [Gradle](http://www.gradle.org), based on [ElectricInsight](http://www.electric-cloud.com/products/electricaccelerator.php?tab=ei) from [Electric Cloud](http://www.electric-cloud.com). The below screenshot is from the gradle build of [Gradle](https://github.com/gradle/gradle) itself, more details [below](#examples):
![Visualization of the gradle Gradle build](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/screenshots/20131106_Gradle_Anno_screenshot.png?raw=true "Visualization of the gradle Gradle build")

### ElectricInsight
ElectricInsight is a powerful tool to visually depict the structure of a software build, down to the file level - empowering build managers to pinpoint performance problems and conflicts in a build. The default usage of ElectricInsight is as an add-on to [ElectricAccelerator](http://www.electric-cloud.com/products/electricaccelerator.php), mining the information produced by ElectricAccelerator to provide an easy-to-understand, graphical representation of the build structure for performance analysis. It provides detailed information and reports on each job on each parallel worker of the build infrastructure, for at-a-glance diagnostics. It can also predict and model how build times would be impacted by adding additional build infrastructure, to help guide hardware investment decisions.

http://www.electric-cloud.com/products/electricaccelerator.php?tab=ei

### <a name="prerequisites"></a>Prerequisites
1. ElectricInsight, which comes bundled with the freely available [ElectricAccelerator Developer Edition](http://www.electric-cloud.com/downloads/software.php?tab=eade&promo=Github_Gradle). (Gated behind a simple registration form)
2. A gradle build

### Usage
1. Make sure you comply to the [prerequisites](#prerequisites)
2. Retrieve the [Gradle init-script](https://github.com/electriccommunity/electricaccelerator/blob/master/GradleAnnotationGenerator/initscript/init-generateanno.gradle) from this project
3. Add the --init-scipt/-I flag to load the [initialization script](http://www.gradle.org/docs/current/userguide/init_scripts.html) when running your gradle build:

```
<command-to-run-your-regular-gradle-build> --init-script <path-to-GradleAnnotationGenerator-init-script>
```
4. Open gradle.anno (the generated Gradle annotation file) with ElectricInsight:

```
einsight gradle.anno
```
5. From here you can interactively explore the ElectricInsight reporting and analysis engine for your gradle build, see some example findings and use-cases [below](#examples).

###  <a name="examples"></a>Example Build Visualizations

##### <a name="example_gradle"></a>Gradle
The [Gradle](https://github.com/gradle/gradle) build is interesting because the workload is heavily dominated by testing, which is forked and hence triggers a large amount of parallelization. During my testing I have built the [Gradle 1.9-rc-2 codebase](http://services.gradle.org/distributions/gradle-1.9-rc-2-src.zip) which was failing in my environment due to some gcc test problems.

##### <a name="example_hibernate"></a>Hibernate-ORM
[Hibernate-ORM](https://github.com/hibernate/hibernate-orm)

##### <a name="example_spring"></a>Spring Framework
[Spring Framework](https://github.com/spring-projects/spring-framework)

##### <a name="example_griffon"></a>Griffon
[Griffon](https://github.com/griffon/griffon)

### Next Steps
I think this project is interesting as-is, but there are obviously a number of interesting extensions/improvements that could be considered. On the top of my head, here are some:
1. Thread Allocation
   Rather than relying on a custom algorithm for determining which thread a particular job is running on, explore extending the Gradle [Task](http://www.gradle.org/docs/current/javadoc/org/gradle/api/Task.html)/[Test](http://www.gradle.org/docs/current/javadoc/org/gradle/api/tasks/testing/TestDescriptor.html) API's with information about which worker/thread currently in use. This would yield a _true_ representation of the how the workload is scheduled and allocated on the build infrastructure. 
2. Dependency Visualization
   Extend the generated annotation with all the dependency information available from the Gradle engine (e.g. [Task.getDependencies](http://www.gradle.org/docs/current/javadoc/org/gradle/api/Task.html#getTaskDependencies()) - there are some commented code in the init-script already touching on this). This additional information combined with more sophisticated structuring of e.g. the project-lifecycle and test-suites could allow for more sophisticated and interesting reporting (e.g. ElectricSimulator, Longest Chain). My thinking here would be to use the submake concept to represent such structural information.
3. Improve flexibility of usage, e.g. by allowing for custom generated annotation-files and for varying amount of annotation detail.


