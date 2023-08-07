ADMIN_EMAIL=admin@email.com
ADMIN_PASSWORD=admin

# Paste your CryoSPARC license
CSLICENSE=example-key
# Container URL
CONTAINER=nvcr.io/nvidian/sae/$(USER)_cryosparc:4.2.1
# Set Number of GPUs to allocate on BCP
NGPU=4
# Instance type
INST=dgx1v.32g.$(NGPU).norm
#INST=dgxa100.80g.$(NGPU).norm



projects:
	ngc workspace create --name $(USER)_cryosparc_projects

container:
	docker build --build-arg EMAIL=$(ADMIN_EMAIL) \
		--build-arg PASSWORD=$(ADMIN_PASSWORD) \
		--build-arg CSLICENSE=$(CSLICENSE) \
		-t $(CONTAINER) .
data:
	docker run --user $(id -u):$(id -g) \
		--entrypoint="" \
		--rm -it -v /tmp/:/data \
		$(CONTAINER) \
		bash -c 'eval $$(/opt/cryosparc/cryosparc_master/bin/cryosparcm env) && cd /data && cryosparcm downloadtest'
	tar -xf /tmp/empiar_10025_subset.tar
	rm /tmp/empiar_10025_subset.tar
	ngc dataset upload --source /tmp/empiar_10025_subset --desc 'https://guide.cryosparc.com/processing-data/get-started-with-cryosparc-introductory-tutorial#step-3-download-the-tutorial-dataset' $(USER)_cryosparc_test_data

run:
	ngc batch run --total-runtime 1D \
		-w $(USER)_cryosparc_projects:/projects:RW \
		--datasetid $(shell ngc dataset list --name $(USER)_cryosparc_test_data --owned --format_type csv | tail -n 1 | cut -f 2 -d ','):/test_data \
		-n test_cryosparc \
		--label _wl___other___cryoem \
		-i $(CONTAINER) \
		-in $(INST) \
		--result /result \
		-c 'sleep 1d' \
		--port 39000 \
		--use-image-entrypoint

benchmark:
	ngc batch run --total-runtime 1D \
		-w $(USER)_cryosparc_projects:/projects:RW \
		--datasetid $(shell ngc dataset list --name $(USER)_cryosparc_test_data --owned --format_type csv | tail -n 1 | cut -f 2 -d ','):/test_data \
		-n test_cryosparc \
		--label _wl___other___cryoem \
		-i $(CONTAINER) \
		-in $(INST) \
		--result /result \
		-c '/workspace/run_T20S.sh' \
		--port 39000 \
		--use-image-entrypoint
push:
	docker push $(CONTAINER)
