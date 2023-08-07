FROM nvidia/cuda:11.8.0-devel-ubuntu18.04

ARG CSVERSION=v4.2.1
ARG CUDAPATH=/usr/local/cuda
# Using /raid on DGX for fast intermediate
ARG SSDPATH=/raid/cryosparc
ARG PROJDIR=/projects
ARG CSLICENSE
ARG FNAME=admin
ARG LNAME=account
ARG EMAIL=admin@email.com
ARG PASSWORD=admin
ENV DEBIAN_FRONTEND noninteractive

# Ensure a license was provided at build time
RUN [ -n "$CSLICENSE" ] || ( echo "Please provide a CryoSPARC license to CSLICENSE"; exit 1; )

RUN apt-get update -y && apt-get install -y --no-install-recommends \
	ctags curl \
	file iputils-ping \
	less sudo \
	vim-nox wget

ENV CS_USER=admin
ENV CS_PASSWORD=$PASSWORD
ENV CS_FNAME=$FNAME
ENV CS_LNAME=$LNAME
ENV CS_EMAIL=$EMAIL
ENV CRYOSPARC_FORCE_USER=true
ENV CRYOSPARC_FORCE_HOSTNAME=true
ENV CRYOSPARC_MASTER_HOSTNAME=localhost
ENV CRYOSPARC_WORKER_HOSTNAME=localhost
ENV CRYOSPARC_SSD_PATH=${SSDPATH}
ENV USER=admin

WORKDIR /workspace

# Install guide:
# https://guide.cryosparc.com/setup-configuration-and-management/how-to-download-install-and-configure/downloading-and-installing-cryosparc

# Get binaries
RUN mkdir /opt/cryosparc/ && chmod -R a+rwX /opt/cryosparc
RUN curl -L https://get.cryosparc.com/download/master-latest/$CSLICENSE | tar -xzf - -C /opt/cryosparc/ \
	&& chmod -R a+rX /opt/cryosparc/cryosparc_master
RUN curl -L https://get.cryosparc.com/download/worker-latest/$CSLICENSE | tar -xzf - -C /opt/cryosparc/ \
	&& chmod -R a+rX /opt/cryosparc/cryosparc_worker

# Install cryosparc_master. Patch install.sh to avoid the commands that will be done when starting the container
# No CUDA or GPUs are visible during docker build.
RUN cd /opt/cryosparc/cryosparc_master && \
	sed -i -e 's/cryosparcm start/echo disabled cryosparcm start/' install.sh && \
	sed -i -e 's/cryosparcm createuser/ echo disabled cryosparcm createuser/' install.sh && \
	sed -i -e 's/echo " Connecting the cryoSPARC worker to the master..."/exit 0/' install.sh
RUN cd /opt/cryosparc/cryosparc_master && \
	./install.sh --standalone --license $CSLICENSE --worker_path /opt/cryosparc/cryosparc_worker \
	--cudapath $CUDAPATH --ssdpath $SSDPATH --initial_password "${CS_PASSWORD}" --initial_email $EMAIL \
	--initial_username "${CS_USER}" --initial_firstname "${CS_FNAME}" --initial_lastname "${CS_LNAME}" && \
	sed -i -e 's/export CRYOSPARC_MASTER_HOSTNAME=.*/export CRYOSPARC_MASTER_HOSTNAME="localhost"/g' /opt/cryosparc/cryosparc_master/config.sh

COPY Instructions.txt /workspace/Instructions.txt
COPY scripts/cryosparc_benchmark.py /workspace/cryosparc_benchmark.py
# Create a launcher
ADD --chmod=755 scripts/run_T20S.sh /workspace/run_T20S.sh
# Activate cryosparc environment on login
#ADD --chmod=755 scripts/profile.d_cryosparc.sh /etc/profile.d/cryosparc.sh
RUN echo 'eval $(/opt/cryosparc/cryosparc_master/bin/cryosparcm env)' >> /etc/bash.bashrc

ENV PROJDIR=${PROJDIR}
ENV SSDPATH=${SSDPATH}

ADD --chmod=755 scripts/entry.sh /opt/cryosparc/entry.sh
ENTRYPOINT ["/opt/cryosparc/entry.sh"]
