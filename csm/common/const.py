# Commands
CSM_INIT_CMD = "init"
CSM_INIT_ACTIONS = ["all", "ha"]
SUPPORT_BUNDLE = "support_bundle"
EMAIL_CONFIGURATION = "email"

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

# Cluster Inventory Related
INVENTORY_FILE = '/etc/csm/cluster.yaml'
KEY_COMPONENTS = 'sw_components'
ADMIN_USER = 'admin_user'
KEY_NODES  = 'nodes'
TYPE_CMU = 'CMU'
TYPE_SSU = 'SSU'
TYPE_S3_SERVER = 'S3_SERVER'

# Config
CSM_FILE = '/etc/csm/csm.conf'
COMPONENTS_FILE = 'COMPONENTS_FILE'
DEFAULT_COMPONENTS_FILE = '/etc/csm/components.yaml'
SUPPORT_BUNDLE_ROOT='SUPPORT_BUNDLE_ROOT'
DEFAULT_SUPPORT_BUNDLE_ROOT='/opt/seagate/bundle'
SSH_TIMEOUT = 'SSH_TIMEOUT'
DEFAULT_SSH_TIMEOUT = 5
USER='user'
DEFAULT_USER='admin'
