FROM centos:7.7.1908

COPY ./csm_agent.rpm /tmp/rpm/
COPY ./experiments/docker/agent/extra/stx.pem /etc/ssl/stx/
COPY ./experiments/docker/agent/extra/database.json /etc/cortx/ha/
COPY ./experiments/docker/agent/extra/ees-schema.json /opt/seagate/eos-prvsnr/generated_configs/healthmap/

RUN yum install -y /tmp/rpm/eos-csm_agent.rpm && ( \
  rm -rf /tmp/rpm ; \
  groupadd haclient ; \
  csm_setup post_install ; \
  csm_setup config --debug ; \
  csm_setup init ; \
  true \
  )

EXPOSE 28101

CMD ["/usr/bin/csm_agent", "--debug"]
