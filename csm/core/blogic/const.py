# Csm Setup
CSM_PATH = "/opt/seagate/eos/csm"
CSM_PIDFILE_PATH = "/var/run/csm"
CSM_CRON_JOB = "/usr/bin/csm_cleanup -d 90"
CSM_SOURCE_CONF_PATH = "{}/conf/etc/csm/".format(CSM_PATH)
CSM_CONF_PATH = "/etc/csm"
ETC_PATH = "/etc"
CSM_CONF_PATH = ETC_PATH + "/csm"
CSM_LOG_PATH = "/var/log/seagate/csm/"
CSM_SOURCE_CONF = "{}/conf/etc/csm/csm.conf".format(CSM_PATH)
CSM_SETUP_LOG_DIR = "/tmp"

# Commands
CSM_SETUP_CMD = 'csm_setup'
CSM_SETUP_CONF = '/etc/csm/setup.yaml'
CSM_SETUP_INDEX = 'CSM_SETUP'
INTERACTIVE_SHELL_HEADER = """
**********************************\n
CSM Interactive Shell 
Type -h or --help for help.\n
***********************************
"""

CLI_PROMPT = "csmcli$ "

SUPPORT_BUNDLE = 'support_bundle'
EMAIL_CONFIGURATION = 'email'
ALERTS_COMMAND = 'alerts'
BASE_DIR = '/opt/seagate/eos'
CSM_INSTALL_BASE_DIR = BASE_DIR + '/csm'
CSM_SCHEMA_BASE_DIR = CSM_INSTALL_BASE_DIR + '/schema'
COMMAND_DIRECTORY = "{}/cli/schema".format(CSM_PATH)
SUB_COMMANDS_PERMISSIONS = "permissions_tag"
HCTL_COMMAND = ['hctl', 'status']
NO_AUTH_COMMANDS = ["support_bundle", "bundle_generate", "csm_bundle_generate",
                    "-h", "--help"]
EXCLUDED_COMMANDS = ['csm_setup']

# CSM Agent Port
CSM_AGENT_HOST = "localhost"
CSM_AGENT_PORT = 8101
CSM_AGENT_BASE_URL = "http://"
TIMEOUT = 300

# Initalization
HA_INIT = '/var/csm/ha_initialized'

# File names
SUMMARY_FILE = 'summary.txt'

# Cluster states
STATE_UP = 'up'
STATE_DOWN = 'down'
STATE_DEGRADED = 'degraded'

# ERROR CODES
SUPPORT_BUNDLE_NOT_FOUND = 1000
OS_PERMISSION_DENIED = 2000

# File Collector
BUNDLE_FILE = 'files.tgz'

# Poll check internal
RESPONSE_CHECK_INTERVAL = 1

# Index
CSM_GLOBAL_INDEX = 'CSM'
INVENTORY_INDEX = 'INVENTORY'
COMPONENTS_INDEX = 'COMPONENTS'
DATABASE_INDEX = 'DATABASE'

# AMQP Consumer Tag
CONSUMER_TAG = 'AMQP_CONSUMER'

# Cluster Inventory Related
INVENTORY_FILE = '/etc/csm/cluster.conf'
KEY_COMPONENTS = 'sw_components'
ADMIN_USER = 'admin_user'
KEY_NODES = 'nodes'
TYPE_CMU = 'CMU'
TYPE_SSU = 'SSU'
TYPE_S3_SERVER = 'S3_SERVER'

# Config
CSM_ETC_DIR = '/etc/csm'
CSM_CONF = '/etc/csm/csm.conf'
CSM_CLUSTER_CONF = '/etc/csm/cluster.conf'
CSM_TMP_FILE_CACHE_DIR = '/tmp/csm/file_cache/transfer'
COMPONENTS_CONF = '/etc/csm/components.yaml'
DATABASE_CONF = '/etc/csm/database.yaml'
SUPPORT_BUNDLE_ROOT = 'SUPPORT_BUNDLE_ROOT'
DEFAULT_SUPPORT_BUNDLE_ROOT =  BASE_DIR + '/bundle'
SSH_TIMEOUT = 'SSH_TIMEOUT'
DEFAULT_SSH_TIMEOUT = 5
USER = 'user'
DEFAULT_USER = 'admin'
CSM_SUPER_USER_ROLE = 'root'
CSM_USER_ROLES = ['manage', 'monitor']
CSM_USER_INTERFACES = ['cli', 'web', 'api']

# Non root user
NON_ROOT_USER = 'csm'
NON_ROOT_USER_PASS = 'csm'

# CSM Alert Related
CSM_ALERT_CMD = 'cmd'
GOOD_ALERT = ['insertion', 'fault_resolved', 'resolved', 'threshold_breached:up']
BAD_ALERT = ['missing', 'fault', 'threshold_breached:low']
SW = 'SW'
HW = 'HW'
ALERT_TYPE = 'type'
HEALTH_ALERT_TYPE = 'alert_type'
ALERT_UUID = 'alert_uuid'
ALERT_STATE = 'state'
ALERT_ENCLOSURE_ID = 'enclosure_id'
ALERT_MODULE_NAME = 'module_name'
ALERT_RESOLVED = 'resolved'
ALERT_ACKNOWLEDGED = 'acknowledged'
ALERT_SEVERITY = 'severity'
ALERT_RESOURCE_TYPE = 'resource_type'
ALERT_MODULE_TYPE = 'module_type'
ALERT_UPDATED_TIME = 'updated_time'
ALERT_CREATED_TIME = 'created_time'
ALERT_INT_DEFAULT = -1
ALERT_TRUE = 1
ALERT_FALSE = 0
ALERT_SENSOR_TYPE = 'sensor_response_type'
ALERT_MESSAGE = 'message'
ALERT_COMMENT = 'comment'
ALERT_SENSOR_INFO = 'sensor_info'
ALERT_MAX_COMMENT_LENGTH = 255
ALERT_SORTABLE_FIELDS = ['created_time', 'updated_time', 'severity', 'resolved', 'acknowledged']
ALERT_SHOW_TIME_HOURS = 24
ALERT_EVENT_DETAILS = 'event_details'
ALERT_EXTENDED_INFO = 'extended_info'
ALERT_SENSOR_INFO = 'sensor_info'
ALERT_EVENTS = 'events'
ALERT_NAME = 'name'
ALERT_COMPONENET_ID = 'component-id'
ALERT_EVENT_REASON = 'event_reason'
ALERT_EVENT_RECOMMENDATION = 'event_recommendation'
ALERT_HEALTH_REASON = 'health-reason'
ALERT_HEALTH_RECOMMENDATION = 'health-recommendation'
ALERT_CURRENT='current'
ALERT_VOLTAGE='voltage'
ALERT_TEMPERATURE='temperature'
ALERT_SENSOR_NAME='sensor-name'
ALERT_CONTAINER='container'
ALERT_DURABLE_ID='durable-id'
ALERT_LOGICAL_VOLUME='logical_volume'
ALERT_VOLUME='volume'
ALERT_SIDEPLANE='sideplane'
ALERT_FAN='fan'
ALERT_HEALTH = 'health'
ALERT_INFO='info'
ALERT_SITE_ID='site_id'
ALERT_CLUSTER_ID='cluster_id'
ALERT_RACK_ID='rack_id'
ALERT_NODE_ID='node_id'
ALERT_RESOURCE_ID='resource_id'
ALERT_EVENT_TIME='event_time'

#Health
HEALTH='health'
OK_HEALTH='ok'
TOTAL='total'
GOOD_HEALTH='good'
HEALTH_SUMMARY='health_summary'


# CSM Schema Path
ALERT_MAPPING_TABLE = '{}/schema/alert_mapping_table.json'.format(CSM_PATH)
HEALTH_CSM_SCHEMA_KEY_MAPPING = '{}/schema/health_csm_schema_key_mapping.json'.format(CSM_PATH)
CSM_SETUP_FILE = '{}/cli/schema/csm_setup.json'.format(CSM_PATH)

#Support Bundle
CLUSTER_INFO_FILE = BASE_DIR + "/eos-prvsnr/pillar/components/cluster.sls"
SSH_USER_NAME = 'root'
COMMANDS_FILE = "{}/schema/commands.yaml".format(CSM_PATH)
SUPPORT_BUNDLE_TAG = "support_bundle"

# CSM Stats Related
AGGREGATION_RULE = '{}/schema/stats_aggregation_rule.json'.format(CSM_PATH)


# CSM Roles Related
ROLES_MANAGEMENT = '{}/schema/roles.json'.format(CSM_PATH)


# UDS/USL
UDS_SERVER_DEFAULT_BASE_URL = 'http://localhost:5000'
UDS_CERTIFICATES_PATH = '/var/csm/tls'
UDS_NATIVE_PRIVATE_KEY_FILENAME = 'native.key'
UDS_NATIVE_CERTIFICATE_FILENAME = 'native.crt'
UDS_DOMAIN_PRIVATE_KEY_FILENAME = 'domain.key'
UDS_DOMAIN_CERTIFICATE_FILENAME = 'domain.crt'


# USL S3 configuration (CES2020 only!)
USL_S3_CONF = '/etc/uds/uds_s3.toml'
#IAM User Related
PASSWORD_SPECIAL_CHARACTER = ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "-", "=", "[", "]", "{", "}", "|", "'"]

# CSM Users
CSM_USER_NAME_MIN_LEN = 3
CSM_USER_NAME_MAX_LEN = 64
CSM_USER_SORTABLE_FIELDS = ['user_id', 'email', 'user_type', 'created_time', 'updated_time']
CSM_USER_DEFAULT_TIMEOUT = 0
CSM_USER_DEFAULT_LANGUAGE = 'English'
CSM_USER_DEFAULT_TEMPERATURE = 'celcius'

#CONSTANT
UNIT_LIST = ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'] 
STRING_MAX_VALUE = 250
PATH_PREFIX_MAX_VALUE = 512
PORT_MIN_VALUE = 0
PORT_MAX_VALUE = 65536

# Email configuration
CSM_SMTP_SEND_TIMEOUT_SEC = 30
CSM_SMTP_RECONNECT_ATTEMPTS = 2
CSM_ALERT_EMAIL_NOTIFICATION_TEMPLATE_REL = '{}/templates/alert_notification_email.html'.format(CSM_PATH)
CSM_ALERT_EMAIL_NOTIFICATION_SUBJECT = 'Alert notification'
CSM_ALERT_NOTIFICATION_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
CSM_SMTP_TEST_EMAIL_ATTEMPTS = 1
CSM_SMTP_TEST_EMAIL_TIMEOUT = 15
CSM_SMTP_TEST_EMAIL_SUBJECT = 'EOS: test email'
CSM_SMTP_TEST_EMAIL_TEMPLATE_REL = '{}/templates/smtp_server_test_email.html'.format(CSM_PATH)

# Audit Log
AUDIT_LOG="/tmp/auditlogs/"
MAX_RESULT_WINDOW=10000

# Syslog constants
LOG_LEVEL="INFO"

# Rsyslog
RSYSLOG_DIR = "/etc/rsyslog.d"
SOURCE_RSYSLOG_PATH = "{0}/conf{1}/csm_logs.conf".format(CSM_PATH, RSYSLOG_DIR)
RSYSLOG_PATH = "{}/csm_logs.conf".format(RSYSLOG_DIR)
SOURCE_SUPPORT_BUNDLE_CONF = "{0}/conf{1}/support_bundle.conf".format(CSM_PATH, RSYSLOG_DIR)
SUPPORT_BUNDLE_CONF = "{}/support_bundle.conf".format(RSYSLOG_DIR)

#logrotate
LOGROTATE_DIR = "/etc/logrotate.d"
SOURCE_LOGROTATE_PATH = "{0}/conf{1}/csm_agent_log.conf".format(CSM_PATH, LOGROTATE_DIR)
LOGROTATE_PATH = "{}/csm_agent_log.conf".format(LOGROTATE_DIR)
