DESPOT_BUILD_DIR := ./bin
TEST_VENV := $(DESPOT_BUILD_DIR)/venv
PRODUCT_VERSION ?= 1.0.0
BUILD_NUMBER ?= 1000
DESPOT_VERSION := $(PRODUCT_VERSION)-$(BUILD_NUMBER)
DESPOT_IMAGE := platform9/despotify:$(DESPOT_VERSION)
DESPOT_IMAGE_TARBALL = $(DESPOT_BUILD_DIR)/despotify-$(DESPOT_VERSION).tar
TAG_FILE := $(DESPOT_BUILD_DIR)/container-full-tag

unit-tests:
	python3 -m unittest test_despotify.py

build-image:
	mkdir -p $(DESPOT_BUILD_DIR)
	docker build -t $(DESPOT_IMAGE) . && \
	docker save --output $(DESPOT_IMAGE_TARBALL) $(DESPOT_IMAGE) && \
	docker rmi -f $(DESPOT_IMAGE)

push-image:
	docker load --input $(DESPOT_IMAGE_TARBALL) && \
	docker push $(DESPOT_IMAGE) && \
	docker rmi -f $(DESPOT_IMAGE)

run:
	docker run $(DESPOT_IMAGE)

$(DESPOT_BUILD_DIR):
	mkdir $@

# This is for IDE development only. The Dockerfile builds its own venv in the container.
${TEST_VENV}: | ${DESPOT_BUILD_DIR}
	virtualenv -p python3 ${TEST_VENV}
	${TEST_VENV}/bin/pip install --no-cache-dir -r requirements.txt

$(TAG_FILE): | $(DESPOT_BUILD_DIR)
	docker build -t $(DESPOT_IMAGE) .
	echo $(DESPOT_IMAGE) > $@

image: $(TAG_FILE)

push: $(TAG_FILE)
	(docker push $(DESPOT_IMAGE) || \
		(echo -n $${DOCKER_PASSWORD} | docker login --password-stdin -u $${DOCKER_USERNAME} && \
		docker push $(DESPOT_IMAGE) && docker logout))
	docker rmi $(DESPOT_IMAGE)

venv: | $(TEST_VENV)

image-clean:
	docker rmi $(DESPOT_IMAGE) || true
	rm -f $(TAG_FILE)

tagfile-clean:
	rm -f $(TAG_FILE)

clean: image-clean
	rm -rf $(DESPOT_BUILD_DIR)
