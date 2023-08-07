#!/bin/bash
set -e
echo "Initializing CryoSPARC container"
[ -e $PROJDIR ] || { echo "Creating project directory"; mkdir $PROJDIR && chmod 777 $PROJDIR; }
[ -e $SSDPATH ] || { echo "Creating SSD directory"; mkdir $SSDPATH && chmod 777 $SSDPATH; }
eval $(/opt/cryosparc/cryosparc_master/bin/cryosparcm env)
cryosparcm start
cryosparcm createuser --email ${CS_EMAIL} --password ${CS_PASSWORD} --username ${CS_USER} --firstname ${CS_FNAME} --lastname ${CS_LNAME}

if [ -e ${PROJDIR}/*benchmark* ]; then
	# https://guide.cryosparc.com/setup-configuration-and-management/software-system-guides/guide-data-management-in-cryosparc-v4.0+#use-case-rescuing-a-project-from-an-inoperable-instance
	echo "Deleting old lock file"
	[ -e ${PROJDIR}/*benchmark*/cs.lock ] && rm ${PROJDIR}/*benchmark*/cs.lock; \
	cs_uid=$(cryosparcm cli "get_id_by_email('${CS_EMAIL}')")
	cryosparcm cli "attach_project(owner_user_id='${cs_uid}', abs_path_export_project_dir='$(ls -d ${PROJDIR}/*benchmark* | head -n 1)')"
else
	ls ${PROJDIR}
	echo "Creating empty project: Benchmark"
	cryosparcm cli "create_empty_project(owner_user_id = '${CS_USER}', project_container_dir = '$PROJDIR', title='Benchmark')"
fi

echo "Connecting worker to master and using $SSDPATH for ssdpath"
/opt/cryosparc/cryosparc_worker/bin/cryosparcw connect --master localhost --worker localhost --ssdpath $SSDPATH
set +e
eval "$@"
