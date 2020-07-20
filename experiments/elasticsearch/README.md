WARNING: This script can wipe ES data from VM, so use it with test VM's only

ES SSC test was splitted into thee main parts:
1) Creating VMs - Requesting three VMs from SSC using REST API. Can take up to 30 minutes.
2) Deploying ES - Installing ES, configuring and starting a cluster
3) Testing ES - Testing ES HA. Powering off primary shard VM, changing data on a new elected VM.

usage: test_es_ssc.py [-h] --url URL --user USER --password PASSWORD
                      --commands COMMANDS [--auth_token AUTH_TOKEN]
                      [--hosts HOSTS]

Arguments:  
  --url Cloud URL "https://example.com/",
  --user Username GID
  --password User password
  --commands Commands divided by comma. They will be executed in the following order: request_3vms,deploy_es,test_es

Optional arguments:
  --auth_token Authorization token for SSC. It will be obtained automatically if ommited.
  --hosts FQDN host names divided by comma

Examples:
Perform all commands at once:
./test_es_ssc.sh --url https://example.com/ --user Username --password Password --commands=request_3vms,deploy_es,test_es

Perform ES deploy process and a test on three VMs:
./test_es_ssc.sh --url https://example.com/ --user Username --password Password --commands=deploy_es,test_es --hosts FQDN1,FQDN2,FQDN3

Perform ES test on three VMs:
./test_es_ssc.sh --url https://example.com/ --user Username --password Password --commands=test_es --hosts FQDN1,FQDN2,FQDN3