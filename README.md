# CryoSPARC on BCP

This is a guide on running single-node CryoSPARC on BCP with the following features:

- Spawns web GUI at startup
- Projects persist between jobs
- Sample data gets mounted into the job
- Runnable on 1-8 GPUs
- Automated T20S benchmark
- CryoSPARC CLI environment added to all shells

## Quickstart

```
# Edit Makefile: Update CSLICENSE, CONTAINER, and INST variables
vim Makefile

# Build and push container
make container; make push

# Create dataset and workapsace
make data projects

# Start CryoSPARC on a 2-GPU instance
make NGPU=2 run
```

## Dependencies

- Docker
- Authenticated NGC CLI
- make

## Building the container

### 1. Add your license

Your CryoSPARC license is used to download CryoSPARC and install it, so it needs to be added to the [Makefile](/Makefile) for build-time.

```
CSLICENSE=example-key
```

### 2. Update container URL

Specify the registry URL that you'll be pushing the CryoSPARC container to by updating `CONTAINER` in the [Makefile](/Makefile).
Since this container will contain your license, make sure that this is not pushed to a public registry.

```
CONTAINER=nvcr.io/nvidian/sae/$(USER)_cryosparc:4.2.1
```

> Note: This is a Makefile, so variables use $(VAR) instead of normal bash ${VAR} notation

### 3. Update admin email and password (optional)

By default, the container creates an admin account for accessing the web portal with the following credentials:

**Email:** admin@email.com
**Password:** admin

These can be changed by editing the makefile or setting `ADMIN_EMAIL` and/or `ADMIN_PASSWORD` at build time.

```
ADMIN_EMAIL=admin@email.com
ADMIN_PASSWORD=admin
```

### 4. Build container

```
make container
```

and if not running on a gpu locally

```
make push
```

## Downloading data and creating your project workspace

After your container is built, the [sample T20S](https://guide.cryosparc.com/processing-data/get-started-with-cryosparc-introductory-tutorial#step-3-download-the-tutorial-dataset) (10025) data can be downloaded and uploaded to a [BCP dataset](https://docs.ngc.nvidia.com/cli/cmd_dataset.html#upload) with the following command:

```
make data
```

Just make sure to have at least 16GB of available space.

For projects to persist between jobs, make sure to mount a projects workspace to `/projects` in the running container.
The [Makefile](/Makefile) has a helper target to create a workspace called `$USER_cryosparc_projects`

```
make projects
```

## Running the container on BCP

Specify the BCP instance type you want to run on by editing the `INST` variable in the [Makefile](/Makefile).
You can list out all instance types by running

```
ngc ace list
```

Just make sure to choose an instance in the ACE you plan on running in.

A CryoSPARC job using 2 GPUs can then be submitted to BCP using the following command:

```
make run
```

This job will run for 1 day and then exit, so make sure to `kill` this job when you're done to free up resources.

## Running the T20S Benchmark

CryoSPARC has a tutorial for running on a subset of the EMPIAR-10025 dataset called T20S.

https://guide.cryosparc.com/processing-data/get-started-with-cryosparc-introductory-tutorial

The T20S sample data used by this workflow was already downloaded with `make dataset`, and is mounted to `/test_data` by both the `run` and `benchmark` targets.

If you don't want to manually run each step in the T20S workflow, CryoSPARC has a convenience workflow

https://guide.cryosparc.com/setup-configuration-and-management/software-system-guides/tutorial-verify-cryosparc-installation-with-the-extensive-workflow-sysadmin-guide

which can also be started on 4 GPUs with the following target:

```
make benchmark
```

> This job will exit after 4 hours because CryoSPARC currently doesn't have a reliable way to wait for jobs to finish
