# pythonScripts
Python scripts that I use to collect quality metrics


# Running Scripts On Docker

## Requirements

* Requires that docker be installed on the machine

## How To Build

> docker build -t \<image name\> .

For examplee, to name the image qa_scripts
> docker build -t qa_scripts .

This will build an image qa_scripts:latest


## How to run

For now, to run it would be

> docker run -ti qa_scripts:latest

From the shell, you can then run the appropriate script:

> python2.7 createTestRuns.py