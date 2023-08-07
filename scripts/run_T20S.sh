#!/bin/bash

# EMPIAR 10025 data mounted to /test_data
# Output saved to workspace

# https://guide.cryosparc.com/setup-configuration-and-management/software-system-guides/tutorial-verify-cryosparc-installation-with-the-extensive-workflow-sysadmin-guide
# https://discuss.cryosparc.com/t/t20-automated-job-submission-after-the-cryosparc-installation/7606/5
# https://guide.cryosparc.com/setup-configuration-and-management/management-and-monitoring/cli


cs_email="admin@email.com"
cs_puid="P1"
cs_lane="default"
cs_uid=$(cryosparcm cli "get_id_by_email('${CS_EMAIL}')")
cs_wuid=$(cryosparcm cli "create_empty_workspace(project_uid='${cs_puid}', created_by_user_id='${cs_uid}', title='T20S Extensive Workflow Run')")
cs_juid=$(cryosparcm cli "create_new_job(job_type='extensive_workflow_bench', project_uid='${cs_puid}', workspace_uid='${cs_wuid}', created_by_user_id='${cs_uid}')")
cryosparcm cli "job_set_param('${cs_puid}', '${cs_juid}', 'all_job_types', True)"  
cryosparcm cli "job_set_param('${cs_puid}', '${cs_juid}', 'blob_paths', '/test_data/*.tif')"  
cryosparcm cli "job_set_param('${cs_puid}', '${cs_juid}', 'gainref_path', '/test_data/norm-amibox05-0.mrc')"  
cryosparcm cli "enqueue_job(project_uid='${cs_puid}', job_uid='${cs_juid}', lane='${cs_lane}')"
# Wait 3hr for the job to complete
sleep 4h
# Command below fails
#cryosparcm cli "wait_job_complete(project_uid='${cs_puid}', job_uid='${cs_juid}', timeout=10800)"
