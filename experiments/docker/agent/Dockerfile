FROM registry.access.redhat.com/rhel7

ARG CSM_AGENT_RPM=./csm_agent.rpm

COPY ${CSM_AGENT_RPM} /tmp/csm_agent.rpm
COPY ./experiments/docker/agent/extra/stx.pem /etc/ssl/stx/
COPY ./experiments/docker/agent/extra/ees-schema.json /opt/seagate/eos-prvsnr/generated_configs/healthmap/

RUN yum install -y /tmp/csm_agent.rpm && ( \
  rm -rf /tmp/csm_agent.rpm ; \
  groupadd haclient ; \
  true \
  )

EXPOSE 28101

VOLUME /etc/csm
VOLUME /etc/cortx

CMD ["/usr/bin/csm_agent", "--debug"]
