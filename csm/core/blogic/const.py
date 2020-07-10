# Csm Setup
CSM_PATH = "/opt/seagate/cortx/csm"
CSM_PIDFILE_PATH = "/var/run/csm"
CSM_CRON_JOB = "/usr/bin/csm_cleanup stats -d 90"
CSM_LOG_PATH = "/var/log/seagate/csm/"
CSM_CLEANUP_LOG_FILE = "csm_cleanup"
CSM_SOURCE_CONF_PATH = "{}/conf/etc/csm/".format(CSM_PATH)
CSM_CONF_PATH = "/etc/csm"
ETC_PATH = "/etc"
CSM_CONF_PATH = ETC_PATH + "/csm"
CSM_SOURCE_CONF = "{}/conf/etc/csm/csm.conf".format(CSM_PATH)
CSM_SETUP_LOG_DIR = "/tmp"
CSM_CONF_FILE_NAME = 'csm.conf'
DB_CONF_FILE_NAME = 'database.yaml'
PLUGIN_DIR = 'eos'
WEB_DIR = 'eos'

# Access log of aiohttp
# format
REST_ACCESS_FORMAT = '%a %P "%r" %s "%{Referer}i" "%{User-Agent}i" %D'
MARSHMALLOW_EXCLUDE = "EXCLUDE"
# Commands
CSM_SETUP_CMD = 'csm_setup'
CSM_SETUP_CONF = '/etc/csm/setup.yaml'
CSM_SETUP_INDEX = 'CSM_SETUP'
INTERACTIVE_SHELL_HEADER = """
**********************************\n
CORTX Interactive Shell
Type -h or --help for help.\n
***********************************
"""

CLI_PROMPT = "cortxcli$ "

EMAIL_CONFIGURATION = 'email'
ALERTS_COMMAND = 'alerts'
BASE_DIR = '/opt/seagate/cortx'
CSM_INSTALL_BASE_DIR = BASE_DIR + '/csm'
CSM_SCHEMA_BASE_DIR = CSM_INSTALL_BASE_DIR + '/schema'
COMMAND_DIRECTORY = "{}/cli/schema".format(CSM_PATH)
SUB_COMMANDS_PERMISSIONS = "permissions_tag"
NO_AUTH_COMMANDS = ["support_bundle", "bundle_generate", "csm_bundle_generate",
                    "-h", "--help", "system"]
EXCLUDED_COMMANDS = ['csm_setup']
HIDDEN_COMMANDS = ["bundle_generate", "csm_bundle_generate",]
RMQ_CLUSTER_STATUS_CMD = 'rabbitmqctl cluster_status'
RUNNING_NODES = 'running_nodes'

# CSM Agent Port
CSM_AGENT_HOST = "localhost"
CSM_AGENT_PORT = 8101
CSM_AGENT_BASE_URL = "http://"
TIMEOUT = 60

# Initalization
HA_INIT = '/var/csm/ha_initialized'

#HA Command
HCTL_NODE = 'hctl node --username {user} --password {pwd} {command}'
HCTL_ERR_MSG = "Failed Script Execution error: {_err} output: {_output}"

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
DEFAULT_SUPPORT_BUNDLE_ROOT = BASE_DIR + '/bundle'
SSH_TIMEOUT = 'SSH_TIMEOUT'
SSH_KEY = 'id_rsa_prvsnr'
DEFAULT_SSH_TIMEOUT = 10
USER = 'user'
DEFAULT_USER = 'admin'
CSM_SUPER_USER_ROLE = 'admin'
CSM_MANAGE_ROLE = 'manage'
CSM_MONITOR_ROLE = 'monitor'
CSM_USER_ROLES = [CSM_MANAGE_ROLE, CSM_MONITOR_ROLE]
CSM_USER_INTERFACES = ['cli', 'web', 'api']

# Non root user
NON_ROOT_USER = 'csm'
NON_ROOT_USER_PASS = 'csm'
CSM_USER_HOME='/opt/seagate/cortx/csm/home/'
HA_CLIENT_GROUP = 'haclient'
SSH_DIR='.ssh'
SSH_PRIVATE_KEY='{}/id_rsa'.format(SSH_DIR)
SSH_PUBLIC_KEY='{}/id_rsa.pub'.format(SSH_DIR)
SSH_AUTHORIZED_KEY='{}/authorized_keys'.format(SSH_DIR)
SSH_CONFIG='{}/config'.format(SSH_DIR)
PRIMARY_ROLE='primary'

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
ALERT_SORTABLE_FIELDS = ['created_time', 'updated_time', 'severity', 'resolved',
                         'acknowledged']
ALERT_EVENT_DETAILS = 'event_details'
ALERT_EXTENDED_INFO = 'extended_info'
ALERT_SENSOR_INFO = 'sensor_info'
ALERT_EVENTS = 'events'
ALERT_NAME = 'name'
ALERT_COMPONENET_ID = 'component_id'
ALERT_EVENT_REASON = 'event_reason'
ALERT_EVENT_RECOMMENDATION = 'event_recommendation'
ALERT_HEALTH_REASON = 'health_reason'
ALERT_HEALTH_RECOMMENDATION = 'health_recommendation'
ALERT_CURRENT = 'current'
ALERT_VOLTAGE = 'voltage'
ALERT_TEMPERATURE = 'temperature'
ALERT_SENSOR_NAME = 'sensor_name'
ALERT_CONTAINER = 'container'
ALERT_DURABLE_ID = 'durable_id'
ALERT_LOGICAL_VOLUME = 'logical_volume'
ALERT_VOLUME = 'volume'
ALERT_SIDEPLANE = 'sideplane'
ALERT_FAN = 'fan'
ALERT_HEALTH = 'health'
ALERT_INFO = 'info'
ALERT_SITE_ID = 'site_id'
ALERT_CLUSTER_ID = 'cluster_id'
ALERT_RACK_ID = 'rack_id'
ALERT_NODE_ID = 'node_id'
ALERT_RESOURCE_ID = 'resource_id'
ALERT_EVENT_TIME = 'event_time'
TIME = 'time'
IEM_ALERT = 'iem_alert'
DESCRIPTION = 'description'
INFORMATIONAL = 'informational'
COMPONENT_ID = 'component_id'
SOURCE_ID = 'source_id'
MODULE_ID = 'module_id'
EVENT_ID = 'event_id'
IEM = 'iem'
SPECIFIC_INFO = 'specific_info'

# Health
OK_HEALTH = 'OK'
NA_HEALTH = 'NA'
TOTAL = 'total'
GOOD_HEALTH = 'good'
HEALTH_SUMMARY = 'health_summary'
RESOURCE_KEY = 'resource_key'
IS_ACTUATOR = 'is_actuator'
IS_NODE1 = 'is_node1'
CHANNEL = 'CHANNEL'
NODE1 = 'node1'
NODE2 = 'node2'
HOST = 'host'
RMQ_HOSTS = 'hosts'
PORT = 'port'
VHOST = 'virtual_host'
UNAME = 'username'
PASS = 'password'
EXCH_TYPE = 'exchange_type'
RETRY_COUNT = 'retry_count'
DURABLE = 'durable'
EXCLUSIVE = 'exclusive'
SLEEP_TIME = 'sleep_time'
EXCH = 'exchange'
EXCH_QUEUE = 'exchange_queue'
ROUTING_KEY = 'routing_key'
ACT_REQ_EXCH = 'actuator_req_exchange'
ACT_REQ_EXCH_QUEUE = 'actuator_req_queue'
ACT_REQ_ROUTING_KEY = 'actuator_req_routing_key'
ENCLOSURE = 'enclosure'
NODE = 'node'
TIME = 'time'
HEADER = 'sspl_ll_msg_header'
UUID = 'uuid'
ACT_REQ_TYPE = 'actuator_request_type'
STORAGE_ENCL = 'storage_enclosure'
ENCL_REQ = 'enclosure_request'
ENCL = 'ENCL:'
NODE_CONTROLLER = 'node_controller'
NODE_REQ = 'node_request'
NODE_HW = 'NDHW:'
KEY = 'key'
HEALTH_FIELD ='health_field'
RES_ID_FIELD = 'res_id_field'
MAPPING_KEY = 'mapping_key'
RESOURCE_LIST = 'resource_list'
DURABLE_ID = 'durable_id'
NODE_RESPONSE = 'node_response'
FETCH_TIME = 'fetch_time'
HOST_ID = 'host_id'
CREATED_TIME = 'created_time'
FAULT_HEALTH = 'Fault'

# CSM Schema Path
ALERT_MAPPING_TABLE = '{}/schema/alert_mapping_table.json'.format(CSM_PATH)
HEALTH_MAPPING_TABLE = '{}/schema/csm_health_schema.json'.format(CSM_PATH)
CSM_SETUP_FILE = '{}/cli/schema/csm_setup.json'.format(CSM_PATH)

# Support Bundle
SSH_USER_NAME = 'root'
COMMANDS_FILE = "{}/schema/commands.yaml".format(CSM_PATH)
SUPPORT_BUNDLE_TAG = "support_bundle;"
SUPPORT_BUNDLE = 'SUPPORT_BUNDLE'
SOS_COMP = 'os'
SB_COMPONENTS = "components"
SB_COMMENT = "comment"
SB_NODE_NAME = "node_name"
SB_BUNDLE_ID = "bundle_id"
SB_BUNDLE_PATH = "bundle_path"
SB_SYMLINK_PATH = "symlink_path"
ROOT_PRIVILEGES_MSG = "Command requires root privileges"
PERMISSION_ERROR_MSG = "Failed to cleanup {path} due to insufficient permissions"

# CSM Stats Related
AGGREGATION_RULE = '{}/schema/stats_aggregation_rule.json'.format(CSM_PATH)

# CSM Roles Related
ROLES_MANAGEMENT = '{}/schema/roles.json'.format(CSM_PATH)
CLI_DEFAULTS_ROLES = '{}/schema/cli_default_roles.json'.format(CSM_PATH)

# S3
S3_HOST = 'S3.host'
S3_IAM_PORT = 'S3.iam_port'
S3_PORT = 'S3.s3_port'
S3_MAX_RETRIES_NUM = 'S3.max_retries_num'
S3_LDAP_LOGIN = 'S3.ldap_login'
S3_LDAP_PASSWORD = 'S3.ldap_password'

S3_IAM_CMD_CREATE_ACCESS_KEY = 'CreateAccessKey'
S3_IAM_CMD_CREATE_ACCESS_KEY_RESP = 'CreateAccessKeyResponse'
S3_IAM_CMD_CREATE_ACCESS_KEY_RESULT = 'CreateAccessKeyResult'
S3_PARAM_ACCESS_KEY = 'AccessKey'
S3_IAM_CMD_LIST_ACCESS_KEYS = 'ListAccessKeys'
S3_IAM_CMD_LIST_ACCESS_KEYS_RESP = 'ListAccessKeysResponse'
S3_IAM_CMD_LIST_ACCESS_KEYS_RESULT = 'ListAccessKeysResult'
S3_PARAM_ACCESS_KEY_METADATA = 'AccessKeyMetadata'
S3_PARAM_IS_TRUNCATED = 'IsTruncated'
S3_PARAM_MARKER = 'Marker'
S3_PARAM_MAX_ITEMS = 'MaxItems'
S3_IAM_CMD_DELETE_ACCESS_KEY = 'DeleteAccessKey'

# UDS/USL
UDS_SERVER_DEFAULT_BASE_URL = 'http://localhost:5000'
UDS_CERTIFICATES_PATH = '/var/csm/tls'
UDS_NATIVE_PRIVATE_KEY_FILENAME = 'native.key'
UDS_NATIVE_CERTIFICATE_FILENAME = 'native.crt'
UDS_DOMAIN_PRIVATE_KEY_FILENAME = 'domain.key'
UDS_DOMAIN_CERTIFICATE_FILENAME = 'domain.crt'

# USL S3 configuration (CES2020 only!)
USL_S3_CONF = '/etc/uds/uds_s3.toml'
# IAM User Related
PASSWORD_SPECIAL_CHARACTER = ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
                              "_", "+", "-", "=", "[", "]", "{", "}", "|", "'"]

# CSM Users
CSM_USER_NAME_MIN_LEN = 3
CSM_USER_NAME_MAX_LEN = 64
CSM_USER_SORTABLE_FIELDS = ['user_id', 'email', 'user_type', 'created_time',
                            'updated_time']
CSM_USER_DEFAULT_TIMEOUT = 0
CSM_USER_DEFAULT_LANGUAGE = 'English'
CSM_USER_DEFAULT_TEMPERATURE = 'celcius'

# CONSTANT
UNIT_LIST = ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
STRING_MAX_VALUE = 250
PATH_PREFIX_MAX_VALUE = 512
PORT_MIN_VALUE = 0
PORT_MAX_VALUE = 65536

SOFTWARE_UPDATE_ID = 'software_update'
FIRMWARE_UPDATE_ID = 'firmware_update'
REPLACE_NODE_ID = 'replace_node'
# Email configuration
CSM_SMTP_SEND_TIMEOUT_SEC = 30
CSM_SMTP_RECONNECT_ATTEMPTS = 2
CSM_ALERT_EMAIL_NOTIFICATION_TEMPLATE_REL = '{}/templates/alert_notification_email.html'.format(
    CSM_PATH)
CSM_ALERT_EMAIL_NOTIFICATION_SUBJECT = 'Alert notification'
CSM_ALERT_NOTIFICATION_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
CSM_SMTP_TEST_EMAIL_ATTEMPTS = 1
CSM_SMTP_TEST_EMAIL_TIMEOUT = 15
CSM_SMTP_TEST_EMAIL_SUBJECT = 'CORTX: test email'
CSM_SMTP_TEST_EMAIL_TEMPLATE_REL = '{}/templates/smtp_server_test_email.html'.format(
    CSM_PATH)

# NTP server config
DATE_TIME_SETTING = 'date_time_settings'
NTP = 'ntp'
NTP_SERVER_ADDRESS = 'ntp_server_address'
NTP_TIMEZONE_OFFSET = 'ntp_timezone_offset'

# Audit Log
AUDIT_LOG = "/tmp/auditlogs/"
MAX_RESULT_WINDOW = 10000

# Syslog constants
LOG_LEVEL = "INFO"

# Set network config
MANAGEMENT_NETWORK = 'management_network_settings'
DATA_NETWORK = 'data_network_settings'
DNS_NETWORK = 'dns_network_settings'
IPV4 = 'ipv4'
NODES = 'nodes'
IP_ADDRESS = 'ip_address'
GATEWAY = 'gateway'
NETMASK = 'netmask'
HOSTNAME = 'hostname'
NAME = 'name'
SUMMARY = 'is_summary'
DNS_SERVER = 'dns_servers'
SEARCH_DOMAIN = 'search_domain'
VIP_NODE = 'VIP'
PRIMARY_NODE = 'Node 0'
SECONDARY_NODE = 'Node 1'
SYSTEM_CONFIG = 'system_config'
IS_DHCP = 'is_dhcp'

# Services
SYSTEM_CONFIG_SERVICE = "system_config_service"
PRODUCT_VERSION_SERVICE = "product_version_service"
CSM_USER_SERVICE = "csm_user_service"

# Rsyslog
RSYSLOG_DIR = "/etc/rsyslog.d"
SOURCE_RSYSLOG_PATH = "{0}/conf{1}/0-csm_logs.conf".format(CSM_PATH, RSYSLOG_DIR)
RSYSLOG_PATH = "{}/0-csm_logs.conf".format(RSYSLOG_DIR)
SOURCE_SUPPORT_BUNDLE_CONF = "{0}/conf{1}/0-support_bundle.conf".format(CSM_PATH, RSYSLOG_DIR)
SUPPORT_BUNDLE_CONF = "{}/0-support_bundle.conf".format(RSYSLOG_DIR)

#cron dire
CRON_DIR="/etc/cron.daily"
SOURCE_CRON_PATH="{0}/conf{1}/es_logrotate.cron".format(CSM_PATH, CRON_DIR)
DEST_CRON_PATH="{}/es_logrotate.cron".format(CRON_DIR)

#logrotate
LOGROTATE_DIR = "/etc/logrotate.d"

# https status code
STATUS_CREATED = 201
STATUS_CONFLICT = 409

SOURCE_LOGROTATE_PATH = "{0}/conf{1}/csm/csm_agent_log.conf".format(CSM_PATH, LOGROTATE_DIR)
CLEANUP_LOGROTATE_PATH = "{0}/conf{1}/common/cleanup_log.conf".format(CSM_PATH, LOGROTATE_DIR)
LOGROTATE_PATH = "{}/".format(LOGROTATE_DIR)

# Service instance literal constant
FW_UPDATE_SERVICE = "fw_update_service"
HOTFIX_UPDATE_SERVICE = "hotfix_update_service"
SECURITY_SERVICE = "security_service"
STORAGE_CAPACITY_SERVICE = "storage_capacity_service"
USL_SERVICE = "usl_service"
MAINTENANCE_SERVICE = "maintenance"
REPLACE_NODE_SERVICE = "replace_node"

# Plugins literal constansts
ALERT_PLUGIN = "alert"
HEALTH_PLUGIN = "health"
S3_PLUGIN = "s3"
PROVISIONER_PLUGIN = "provisioner"

# REST METHODS
POST = "POST"
GET = "GET"
PUT = "PUT"
PATCH = "PATCH"
DELETE = "DELETE"

# Capacity api related constants
FILESYSTEM_STAT_CMD = 'hctl status --json'
TOTAL_SPACE = 'fs_total_disk'
FREE_SPACE = 'fs_free_disk'
SIZE = 'size'
USED = 'used'
AVAILABLE = 'avail'
USAGE_PERCENTAGE = 'usage_percentage'

# Keys for  Description
DECRYPTION_KEYS = {
    "CHANNEL.password": "sspl",
    "S3.ldap_password": "openldap"
}
CLUSTER_ID_KEY = "PROVISIONER.cluster_id"
# Provisioner status
PROVISIONER_CONFIG_TYPES = ['network', 'firmware', 'hotfix']

# Provisioner Plugin constant
NODE_LIST_KEY='cluster:node_list'
GRAINS_GET = 'grains.get'
PILLAR_GET = 'pillar.get'
S3 = 'S3'
RMQ = 'rmq'
CHANNEL = 'CHANNEL'
USERNAME = "username"
PASSWORD = 'password'
SECRET = 'secret'
IAM_ADMIN = 'iam_admin'
OPENLDAP = 'openldap'
SSPL = 'sspl:LOGGINGPROCESSOR'
LDAP_LOGIN = 'ldap_login'
LDAP_PASSWORD = 'ldap_password'
CLUSTER_ID = 'cluster_id'
PROVISIONER='PROVISIONER'
LOCAL='local'
RET='ret'
DEBUG='debug'
NA='NA'
GET_NODE_ID='get_node_id'

#Deployment Mode
DEPLOYMENT = 'DEPLOYMENT'
MODE = 'mode' 
DEV = 'dev'

# System config list
SYSCONFIG_TYPE = ['management_network_settings', 'data_network_settings',
                  'dns_network_settings', 'date_time_settings', 'notifications']
#Maintenance
STATE_CHANGE = "Successfully put {node} on {state} state"
ACTION = "action"
NODE_STATUS = "node_status"
STANDBY = "standby"
SHUTDOWN = "shutdown"
START = "start"
STOP = "stop"
RESOURCE_NAME = "resource_name"
REPLACE_NODE = "replace_node"
NODE_STATUS = "node_status"
INVALID_PASSWORD = f"Invalid {PASSWORD}"
STATUS_CHECK_FALED = "Node Status Can't be Checked. HCTL Command Failed"
SHUTDOWN_NODE_FIRST =  "Please Shutdown the Resource First Before Replacing."
NODE_REPLACEMENT_ALREADY_RUNNING = "Node Replacement is Already in Progress."
NODE_REPLACEMENT_STARTED = "Node Replacement for {resource_name} Started."
#Services
HEALTH_SERVICE = "health_service"
ALERTS_SERVICE = "alerts_service"

ALERT_RETRY_COUNT = 3
COMMON = "common"

SUPPORT_BUNDLE_SHELL_COMMAND = "sh {csm_path}/cli/schema/create_support_bundle.sh {args}"
RMQ_CLUSTER_STATUS_RETRY_COUNT = 3
SUPPORT_MSG = "Please contact Seagate Support. Visit https://www.seagate.com/support/contact-support/ for details on how to contact Seagate Support."
ID = "id"
CLUSTER = "cluster"
NETWROK = "network"
DATA_NW = "data_nw"
ROAMING_IP = "roaming_ip"
CONSUL_HOST_KEY = "databases.consul_db.config.host"
MINION_NODE1_ID = "srvnode-1"
MINION_NODE2_ID = "srvnode-2"
SAS_RESOURCE_TYPE = "node:interface:sas"
ACTUATOR_REQUEST_LIST = ["enclosure:fru:sideplane", "enclosure:fru:disk", \
    "enclosure:fru:psu", "enclosure:fru:controller", "enclosure:fru:fan", \
    "enclosure:eos:logical_volume", "enclosure:interface:sas", \
    "enclosure:sensor:current", "enclosure:sensor:temperature", \
    "enclosure:sensor:voltage", "node:sensor:temperature", "node:fru:disk", \
    "node:fru:psu", "node:fru:fan", "node:sensor:current", "node:sensor:voltage", \
    "node:interface:sas", "node:interface:nw:cable"]
