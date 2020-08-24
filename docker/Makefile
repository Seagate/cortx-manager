# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

CENTOS_RELEASE  := 7
NAMESPACE       := registry.gitlab.mero.colo.seagate.com
DOCKER          := docker

INAME = $(@:%-image=%)
CNAME = $(@:%-container=%)

.PHONY: images
images: docker-image-latest \
        docker-image-7.6 \
        docker-image-eos

.PHONY: docker-image-latest docker-image-7
docker-image-latest docker-image-7: csm-devel-image

.PHONY: docker-image-7.6
docker-image-7.6: CENTOS_RELEASE := 7.6
docker-image-7.6: csm-devel-image

.PHONY: docker-image-eos
docker-image-eos: CENTOS_RELEASE := eos
docker-image-eos: csm-devel-image


.PHONY: csm-devel-image
csm-devel-image:
	cd $(INAME) \
	&& tar -ch . \
	   | $(DOCKER) build \
			--build-arg CENTOS_RELEASE=$(CENTOS_RELEASE) \
			-t $(NAMESPACE)/$(INAME):$(CENTOS_RELEASE) \
			-t $(NAMESPACE)/eos/csm:$(CENTOS_RELEASE) \
			$(DOCKER_OPTS) -

.PHONY: push
name := csm*
tag  := *
push:
	@for img in $$(docker images --filter=reference='$(NAMESPACE)/$(name):$(tag)' \
				    --format '{{.Repository}}:{{.Tag}}' | grep -v none) \
		    $$(docker images --filter=reference='$(NAMESPACE)/eos/$(name):$(tag)' \
				    --format '{{.Repository}}:{{.Tag}}' | grep -v none) ; \
	do \
		echo "---> $$img" ; \
		$(DOCKER) push $$img ; \
	done

.PHONY: clean
clean:
	@for img in $$(docker images --filter=reference='$(NAMESPACE)/$(name):$(tag)' \
				    --format '{{.Repository}}:{{.Tag}}') \
		    $$(docker images --filter=reference='$(NAMESPACE)/eos/$(name):$(tag)' \
				    --format '{{.Repository}}:{{.Tag}}') ; \
	do \
		echo "---> $$img" ; \
		$(DOCKER) rmi $$img ; \
	done

.PHONY: help
help:
	@echo '  images  - create docker images for CI environment'
	@echo "  push    - upload local $(NAMESPACE)/$(name)* images to docker registry"
	@echo "  clean   - remove local $(NAMESPACE)/$(name)* images"
