# Commands
CSM_SETUP_CMD = "setup"
CSM_SETUP_ACTIONS = ["init"]
SUPPORT_BUNDLE = "support_bundle"
EMAIL_CONFIGURATION = "email"

# CSM Agent Port
CSM_AGENT_PORT=8082

# Initalization
HA_INIT = '/var/csm/ha_initialized'

# File names
SUMMARY_FILE = "summary.txt"

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

# AMQP Consumer Tag
CONSUMER_TAG = 'AMQP_CONSUMER'

# Cluster Inventory Related
INVENTORY_FILE = '/etc/csm/cluster.conf'
KEY_COMPONENTS = 'sw_components'
ADMIN_USER = 'admin_user'
KEY_NODES  = 'nodes'
TYPE_CMU = 'CMU'
TYPE_SSU = 'SSU'
TYPE_S3_SERVER = 'S3_SERVER'

# Config
CSM_CONF = '/etc/csm/csm.conf'
CSM_CLUSTER_CONF = '/etc/csm/cluster.conf'
COMPONENTS_FILE = 'COMPONENTS_FILE'
DEFAULT_COMPONENTS_FILE = '/etc/csm/components.yaml'
SUPPORT_BUNDLE_ROOT='SUPPORT_BUNDLE_ROOT'
DEFAULT_SUPPORT_BUNDLE_ROOT='/opt/seagate/bundle'
SSH_TIMEOUT = 'SSH_TIMEOUT'
DEFAULT_SSH_TIMEOUT = 5
USER='user'
DEFAULT_USER='admin'

# CSM Alert Related
CSM_ALERT_CMD = 'cmd'
FAN_ALERT = 'enclosure_fan_module_alert'
GOOD_ALERT = ['insertion', 'fault_resolved']
BAD_ALERT = ['missing', 'fault']
ALERT_ID = 'id'
ALERT_TYPE = 'type'
ALERT_UUID = 'alert_uuid'
ALERT_STATUS = 'status'
ALERT_HW = 'hw'
ALERT_ENCLOSURE_ID = 'enclosure_id'
IN_ALERT_ENCLOSURE_ID = 'enclosure-id'
ALERT_MODULE_NAME = 'module_name'
ALERT_DESCRIPTION = 'description'
ALERT_HEALTH = 'health'
ALERT_HEALTH_REASON = 'health-reason'
ALERT_HEALTH_RECOMMENDATION = 'health_recommendation'
IN_ALERT_HEALTH_RECOMMENDATION = 'health-recommendation'
ALERT_LOCATION = 'location'
ALERT_RESOLVED = 'resolved'
ALERT_ACKNOWLEDGED = 'acknowledged'
ALERT_SEVERITY = 'severity'
ALERT_INFO = 'info'
ALERT_FAN_MODULE = 'fan_module'
ALERT_STATE = 'state'
ALERT_EXTENDED_INFO = 'extended_info'
ALERT_RESOURCE_TYPE = 'resource_type'
ALERT_OTHER_DETAILS = 'other_details'
ALERT_MODULE_TYPE = 'module_type'
ALERT_UPDATED_TIME = 'updated_time'
ALERT_CREATED_TIME = 'created_time'
ALERT_INT_DEFAULT = -1
ALERT_TRUE = 1
ALERT_FALSE = 0

# CSM Schema Path
CSM_HW_SCHEMA = '/opt/seagate/csm/schema/csm_hw_alert.json'
