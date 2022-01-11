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

import os
import time
import ldap
from cortx.utils.product_features import unsupported_features
from marshmallow.exceptions import ValidationError
from csm.common.payload import Json, Text
from ipaddress import ip_address
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from csm.conf.setup import Setup, CsmSetupError
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from cortx.utils.validator.v_network import NetworkV
from csm.common.process import SimpleProcess
from ldif import LDIFRecordList
from cortx.utils.message_bus import MessageBusAdmin,MessageBus


class Configure(Setup):
    """
    Perform configuration for csm
        : Move conf file to etc
    Config is used to move update conf files one time configuration
    """
    def __init__(self):
        super(Configure, self).__init__()
        Log.info("Triggering csm_setup config")
        self._replacement_node_flag = os.environ.get(
            "REPLACEMENT_NODE") == "true"
        if self._replacement_node_flag:
            Log.info("REPLACEMENT_NODE flag is set")

    async def execute(self, command):
        """
        :param command:
        :return:
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(const.CONFIG_URL))
            self.config_path = self._set_csm_conf_path()
            self._copy_skeleton_configs()
            Conf.load(const.CSM_GLOBAL_INDEX,
                    f"yaml://{self.config_path}/{const.CSM_CONF_FILE_NAME}")
            Conf.load(const.DATABASE_INDEX,
                    f"yaml://{self.config_path}/{const.DB_CONF_FILE_NAME}")
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")

        self.force_action = command.options.get('f')
        Log.info(f"Force flag: {self.force_action}")
        services = command.options.get("services")
        if ',' in services:
            services = services.split(",")
        elif 'all' in services:
            services = ["agent", "web", "cli"]
        else:
            services=[services]
        self.execute_web_and_cli(command.options.get("config_url"),
                                    services,
                                    command.sub_command_name)
        if not "agent" in services:
            return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
        self._prepare_and_validate_confstore_keys()

        self.cluster_id = Conf.get(const.CONSUMER_INDEX,
                        self.conf_store_keys[const.KEY_CLUSTER_ID])
        self.set_csm_endpoint()
        self.set_s3_info()
        self.create_topics()
        try:
            self._configure_csm_ldap_schema()
            self._set_user_collection()
            await self._create_cluster_admin(self.force_action)
            self.create()
            for count in range(0, 4):
                try:
                    await self._set_unsupported_feature_info()
                    break
                except Exception as e_:
                    Log.warn(f"Unable to connect to ES. Retrying : {count+1}. {e_}")
                    time.sleep(2**count)
        except ValidationError as ve:
            Log.error(f"Validation Error: {ve}")
            raise CsmSetupError(f"Validation Error: {ve}")
        except Exception as e:
            import traceback
            err_msg = (f"csm_setup config command failed. Error: "
                       f"{e} - {str(traceback.format_exc())}")
            Log.error(err_msg)
            raise CsmSetupError(err_msg)
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
                const.KEY_SERVER_NODE_INFO:f"{const.NODE}>{self.machine_id}",
                const.KEY_SERVER_NODE_TYPE:f"{const.ENV_TYPE_KEY}",
                const.KEY_CLUSTER_ID:f"{const.NODE}>{self.machine_id}>{const.CLUSTER_ID}",
                const.S3_IAM_ENDPOINTS: f"{const.S3_IAM_ENDPOINTS_KEY}",
                const.S3_DATA_ENDPOINT: f"{const.S3_DATA_ENDPOINTS_KEY}",
                const.CSM_AGENT_ENDPOINTS:f"{const.CSM_AGENT_ENDPOINTS_KEY}",
                const.S3_AUTH_ADMIN: f"{const.S3_AUTH_ADMIN_KEY}",
                const.OPENLDAP_ROOT_ADMIN:f"{const.OPENLDAP_ROOT_ADMIN_KEY}",
                const.OPENLDAP_ROOT_SECRET:f"{const.OPENLDAP_ROOT_SECRET_KEY}",
                const.S3_AUTH_SECRET: f"{const.S3_AUTH_SECRET_KEY}"
                })

        Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))

    def create(self):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """

        Log.info("Creating CSM Conf File on Required Location.")
        if self._is_env_dev:
            Conf.set(const.CSM_GLOBAL_INDEX, f"{const.DEPLOYMENT}>{const.MODE}",
                     const.DEV)
        Conf.save(const.CSM_GLOBAL_INDEX)
        Conf.save(const.DATABASE_INDEX)

    def set_csm_endpoint(self):
        Log.info("Setting csm endpoint in csm config")
        csm_endpoint = Conf.get(const.CONSUMER_INDEX, const.CSM_AGENT_ENDPOINTS_KEY)
        csm_protocol, csm_host, csm_port = self._parse_endpoints(csm_endpoint)
        Conf.set(const.CSM_GLOBAL_INDEX, const.AGENT_ENDPOINTS, csm_endpoint)
        # Not considering Hostname. Bydefault 0.0.0.0 used
        # Conf.set(const.CSM_GLOBAL_INDEX, const.AGENT_HOST, csm_host)
        if csm_protocol == 'https':
            Conf.set(const.CSM_GLOBAL_INDEX, 'DEBUG>http_enabled', 'false')
        Conf.set(const.CSM_GLOBAL_INDEX, const.HTTPS_PORT, csm_port)
        Conf.set(const.CSM_GLOBAL_INDEX, const.AGENT_PORT, csm_port)
        Conf.set(const.CSM_GLOBAL_INDEX, const.AGENT_BASE_URL, csm_protocol+'://')

    def set_s3_info(self):
        """
        This Function will set s3  related configurations.
        :return:
        """
        Log.info("Setting S3 configurations in csm config")
        iam_endpoint = Conf.get(const.CONSUMER_INDEX, const.S3_IAM_ENDPOINTS_KEY)
        iam_protocol, iam_host, iam_port = self._parse_endpoints(iam_endpoint)
        Conf.set(const.CSM_GLOBAL_INDEX, const.IAM_ENDPOINT, iam_endpoint)
        Conf.set(const.CSM_GLOBAL_INDEX, const.IAM_HOST, iam_host)
        Conf.set(const.CSM_GLOBAL_INDEX, const.IAM_PORT, iam_port)
        Conf.set(const.CSM_GLOBAL_INDEX, const.IAM_PROTOCOL, iam_protocol)

        data_endpoint = Conf.get(const.CONSUMER_INDEX, const.S3_DATA_ENDPOINTS_KEY)
        data_protocol, data_host, data_port = self._parse_endpoints(data_endpoint)
        Conf.set(const.CSM_GLOBAL_INDEX, const.S3_DATA_ENDPOINT, data_endpoint)
        Conf.set(const.CSM_GLOBAL_INDEX, const.S3_DATA_HOST, data_host)
        Conf.set(const.CSM_GLOBAL_INDEX, const.S3_DATA_PORT, data_port)
        Conf.set(const.CSM_GLOBAL_INDEX, const.S3_DATA_PROTOCOL, data_protocol)

        s3_auth_user = Conf.get(const.CONSUMER_INDEX, const.S3_AUTH_ADMIN_KEY)
        s3_auth_secret = Conf.get(const.CONSUMER_INDEX, const.S3_AUTH_SECRET_KEY)
        Conf.set(const.CSM_GLOBAL_INDEX, const.S3_AUTH_USER_CONF, s3_auth_user)
        Conf.set(const.CSM_GLOBAL_INDEX, const.S3_AUTH_SECRET_CONF, s3_auth_secret)

    async def _set_unsupported_feature_info(self):
        """
        This method stores CSM unsupported features in two ways:
        1. It first gets all the unsupported features lists of the components,
        which CSM interacts with. Add all these features as CSM unsupported
        features. The list of components, CSM interacts with, is
        stored in csm.conf file. So if there is change in name of any
        component, csm.conf file must be updated accordingly.
        2. Installation/envioronment type and its mapping with CSM unsupported
        features are maintained in unsupported_feature_schema. Based on the
        installation/environment type received as argument, CSM unsupported
        features can be stored.
        """

        def get_component_list_from_features_endpoints():
            Log.info("Get Component List.")
            feature_endpoints = Json(
                const.FEATURE_ENDPOINT_MAPPING_SCHEMA).load()
            component_list = [feature for v in feature_endpoints.values() for
                              feature in v.get(const.DEPENDENT_ON)]
            return list(set(component_list))
        try:
            Log.info("Set unsupported feature list to ES.")
            unsupported_feature_instance = unsupported_features.UnsupportedFeaturesDB()
            components_list = get_component_list_from_features_endpoints()
            unsupported_features_list = []
            for component in components_list:
                Log.info(f"Fetch Unsupported Features for {component}.")
                unsupported = await unsupported_feature_instance.get_unsupported_features(
                    component_name=component)
                for feature in unsupported:
                    unsupported_features_list.append(
                        feature.get(const.FEATURE_NAME))
            csm_unsupported_feature = Json(
                const.UNSUPPORTED_FEATURE_SCHEMA).load()
            for setup in csm_unsupported_feature[const.SETUP_TYPES]:
                if setup[const.NAME] == self._setup_info[const.STORAGE_TYPE]:
                    unsupported_features_list.extend(
                        setup[const.UNSUPPORTED_FEATURES])
            unsupported_features_list = list(set(unsupported_features_list))
            unique_unsupported_features_list = list(
                filter(None, unsupported_features_list))
            if unique_unsupported_features_list:
                Log.info("Store Unsupported Features.")
                await unsupported_feature_instance.store_unsupported_features(
                    component_name=str(const.CSM_COMPONENT_NAME),
                    features=unique_unsupported_features_list)
            else:
                Log.info("Unsupported features list is empty.")
        except Exception as e_:
            Log.error(f"Error in storing unsupported features: {e_}")
            raise CsmSetupError(f"Error in storing unsupported features: {e_}")

    def _configure_csm_ldap_schema(self):
        """
        Configure openLdap for CORTX Users
        """
        if not os.path.exists(const.TMP_CSM):
            os.mkdir(const.TMP_CSM)
        Log.info("Openldap configuration started for Cortx users.")
        ldap_root_secret = Conf.get(const.CSM_GLOBAL_INDEX, const.OPEN_LDAP_ADMIN_SECRET)
        _rootdnpassword = self._decrypt_secret(ldap_root_secret,self.cluster_id,
                    Conf.get(const.CSM_GLOBAL_INDEX, "S3>password_decryption_key"))
        csm_ldap_secret =  Conf.get(const.CSM_GLOBAL_INDEX, const.LDAP_AUTH_CSM_SECRET)
        csm_admin_ldap_password = self._decrypt_secret(csm_ldap_secret,self.cluster_id,
                        Conf.get(const.CSM_GLOBAL_INDEX, "S3>password_decryption_key"))
        if not (_rootdnpassword or csm_admin_ldap_password):
            raise CsmSetupError("Failed to fetch LDAP password.")
        csm_schema_version = Conf.get(const.CSM_GLOBAL_INDEX,
                                    const.LDAP_AUTH_CSM_SCHEMA_VERSION)
        base_dn = Conf.get(const.CSM_GLOBAL_INDEX,
                                    f"{const.OPENLDAP_KEY}>{const.BASE_DN_KEY}")
        bind_base_dn = Conf.get(const.CSM_GLOBAL_INDEX,
                                    f"{const.OPENLDAP_KEY}>{const.BIND_BASE_DN_KEY}")
        ldap_user = const.LDAP_USER.format(
            Conf.get(const.CSM_GLOBAL_INDEX, const.LDAP_AUTH_CSM_USER),base_dn)

        ldap_root_admin_user = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.OPENLDAP_ROOT_ADMIN], 'admin')

        Log.info(f"Updating base dn in {const.CORTXUSER_INIT_LDIF}")
        tmpl_init_data = Text(const.CORTXUSER_INIT_LDIF).load()
        tmpl_init_data = tmpl_init_data.replace('<version>',f"{csm_schema_version}")
        tmpl_init_data = tmpl_init_data.replace('<base-dn>',base_dn)
        Text(const.CSM_LDAP_INIT_FILE_PATH).dump(tmpl_init_data)

        for each_server_url in Setup._get_ldap_server_url():
            for count in range(0, 4):
                try:
                    # Insert cortxuser schema
                    Log.info(f"Inserting Cortxuser schema to server: {each_server_url}")
                    self._perform_ldif_parsing(each_server_url, const.CORTXUSER_SCHEMA_LDIF,f'cn={ldap_root_admin_user},cn=config',_rootdnpassword)

                    # Initialize dc=csm,dc=seagate,dc=com
                    Log.info(f"Initializing dc=csm,dc=seagate,dc=com to server: {each_server_url}")
                    self._perform_ldif_parsing(each_server_url, const.CSM_LDAP_INIT_FILE_PATH, bind_base_dn, _rootdnpassword)

                    # Create CSM admin user in LDAP
                    Log.info(f"Creating CSM ldap admin user to server: {each_server_url}")
                    self._create_csm_ldap_user(each_server_url)
                    # Setup necessary permissions
                    Log.info(f"Setup necessary permissions to {ldap_user} on server: {each_server_url}")
                    self._setup_ldap_permissions(each_server_url, base_dn, ldap_user)
                    break
                except Exception as e_:
                    Log.warn(f"Failed while Configuring LDAP for CSM. Retrying : {count+1}.\n {e_}")
                    time.sleep(2**count)

        Setup._run_cmd(f'rm -rf {const.CSM_LDAP_INIT_FILE_PATH}')

        # Create Cortx Account
        Log.info(f"Updating base dn in {const.CORTXUSER_ACCOUNT_LDIF}")
        tmpl_useracc_data = Text(const.CORTXUSER_ACCOUNT_LDIF).load()
        tmpl_useracc_data = tmpl_useracc_data.replace('<version>',csm_schema_version)
        tmpl_useracc_data = tmpl_useracc_data.replace('<base-dn>',base_dn)
        Text(const.CSM_LDAP_ACC_FILE_PATH).dump(tmpl_useracc_data)
        self._perform_ldif_parsing(Setup._get_ldap_url(), const.CSM_LDAP_ACC_FILE_PATH, ldap_user, csm_admin_ldap_password)
        Setup._run_cmd(f'rm -rf {const.CSM_LDAP_ACC_FILE_PATH}')
        Log.info("Openldap configuration completed for Cortx users.")

    def _setup_ldap_permissions(self, ldap_url, base_dn, ldap_user):
        """
        Setup necessary access permissions
        """
        dn = 'olcDatabase={2}mdb,cn=config'
        self._modify_ldap_attribute(ldap_url, dn, 'olcAccess', '{1}to dn.sub="dc=csm,'+base_dn+'" by dn.base="'+ldap_user+'" read by self')
        self._modify_ldap_attribute(ldap_url, dn, 'olcAccess', '{1}to dn.sub="dc=csm,'+base_dn+'" by dn.base="'+ldap_user+'" write by self')

    def _create_csm_ldap_user(self, ldap_url):
        """
        Create CSM ldap user
        """
        Log.info("Creating csm ldap user.")
        ldap_root_secret = Conf.get(const.CSM_GLOBAL_INDEX, const.OPEN_LDAP_ADMIN_SECRET)
        _rootdnpassword = self._decrypt_secret(ldap_root_secret,self.cluster_id,
                        Conf.get(const.CSM_GLOBAL_INDEX, "S3>password_decryption_key"))
        base_dn = Conf.get(const.CSM_GLOBAL_INDEX,
                                    f"{const.OPENLDAP_KEY}>{const.BASE_DN_KEY}")
        bind_base_dn = Conf.get(const.CSM_GLOBAL_INDEX,
                                    f"{const.OPENLDAP_KEY}>{const.BIND_BASE_DN_KEY}")
        ldap_user = Conf.get(const.CSM_GLOBAL_INDEX, const.LDAP_AUTH_CSM_USER)
        csm_ldap_secret =  Conf.get(const.CSM_GLOBAL_INDEX, const.LDAP_AUTH_CSM_SECRET)
        csm_admin_ldap_password = self._decrypt_secret(csm_ldap_secret,self.cluster_id,
                        Conf.get(const.CSM_GLOBAL_INDEX, "S3>password_decryption_key"))
        tmpl_init_data = Text(const.CSM_LDAP_ADMIN_USER_LDIF).load()
        tmpl_init_data = tmpl_init_data.replace('<base-dn>',base_dn)
        tmpl_init_data = tmpl_init_data.replace('<csm-admin-user>',ldap_user)
        tmpl_init_data = tmpl_init_data.replace('<csm-admin-password>',csm_admin_ldap_password)
        Text(const.CSM_LDAP_ADMIN_FILE_PATH).dump(tmpl_init_data)
        self._perform_ldif_parsing(ldap_url, const.CSM_LDAP_ADMIN_FILE_PATH, bind_base_dn, _rootdnpassword)
        Setup._run_cmd(f'rm -rf {const.CSM_LDAP_ADMIN_FILE_PATH}')

    def _modify_ldap_attribute(self, ldap_url, dn, attribute, value):
        ldap_root_admin_user = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.OPENLDAP_ROOT_ADMIN], 'admin')
        _bind_dn = f"cn={ldap_root_admin_user},cn=config"
        ldap_root_secret = Conf.get(const.CSM_GLOBAL_INDEX, const.OPEN_LDAP_ADMIN_SECRET)
        _ldappasswd= self._decrypt_secret(ldap_root_secret,self.cluster_id,
                    Conf.get(const.CSM_GLOBAL_INDEX, "S3>password_decryption_key"))
        try:
            self._connect_to_ldap_server(ldap_url, _bind_dn, _ldappasswd)
            mod_attrs = [(ldap.MOD_ADD, attribute, bytes(str(value), 'utf-8'))]
            Log.info(f"Modifying attribute permissions: {mod_attrs}")
            self._ldap_conn.modify_s(dn, mod_attrs)
        except Exception as e:
            if isinstance(e, ldap.TYPE_OR_VALUE_EXISTS):
                Log.warn(f"Exception: Type or Value already exists: {e}")
            else:
                Log.error('Error while modifying attribute- '+ attribute )
                raise Exception('Error while modifying attribute' + attribute)
        finally:
            if self._ldap_conn:
                self._disconnect_from_ldap()

    def _perform_ldif_parsing(self, ldap_url, filename, binddn, pwd):
        parser = LDIFRecordList(open(filename, 'r'))
        parser.parse()
        for dn, entry in parser.all_records:
            add_record = list(entry.items())
            self._add_attribute(ldap_url, binddn, dn, add_record, pwd)

    def _add_attribute(self, ldap_url, binddn, dn, record, pwd):
        try:
            self._connect_to_ldap_server(ldap_url, binddn, pwd)
            self._ldap_conn.add_s(dn, record)
        except Exception as e:
            if isinstance(e, ldap.TYPE_OR_VALUE_EXISTS):
                Log.warn(f"Exception:Type already exist: {e}")
            elif isinstance(e, ldap.OTHER):
                Log.warn(f"Exception:Attribute  Error: {e}")
            elif isinstance(e, ldap.ALREADY_EXISTS):
                Log.warn(f"Exception: Resource already Exist: {e}")
            else:
                Log.error('Error while adding attribute')
                raise Exception('Error while adding attribute')
        finally:
            if self._ldap_conn:
                self._disconnect_from_ldap()


    def _set_user_collection(self):
        """
        Sets collection for User model in database.conf
        :return:
        """
        base_dn = Conf.get(const.CSM_GLOBAL_INDEX,
                                    f"{const.OPENLDAP_KEY}>{const.BASE_DN_KEY}")
        csm_schema_version = Conf.get(const.CSM_GLOBAL_INDEX,
                                    const.LDAP_AUTH_CSM_SCHEMA_VERSION)
        models_list = Conf.get(const.DATABASE_INDEX,"models")
        for record in models_list:
            if record['import_path'] == 'csm.core.data.models.users.User':
                record['config']['openldap']['collection'] = const.CORTXUSERS_DN.format(csm_schema_version,base_dn)
        Conf.set(const.DATABASE_INDEX,"models",models_list)
        Conf.save(const.DATABASE_INDEX)

    def _create_perf_stat_topic(self, mb_admin):
        message_type = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_MSG_TYPE)
        partitions = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_PARTITIONS)
        retention_size = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_RETENTION_SIZE))
        retention_period = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_PERF_STAT_RETENTION_PERIOD))
        if not message_type in mb_admin.list_message_types():
            Log.info(f"Registering message_type:{message_type}")
            mb_admin.register_message_type(message_types=[message_type], partitions=partitions)
            mb_admin.set_message_type_expire(message_type,
                                            expire_time_ms=retention_period,
                                            data_limit_bytes=retention_size)
        else:
            Log.info(f"message_type:{message_type} already exists.")
    
    def _create_cluster_stop_topic(self, mb_admin):
        message_type = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_MSG_TYPE)
        partitions = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_PARTITIONS)
        retention_size = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_RETENTION_SIZE))
        retention_period = int(Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_CLUSTER_STOP_RETENTION_PERIOD))
        if not message_type in mb_admin.list_message_types():
            Log.info(f"Registering message_type:{message_type}")
            mb_admin.register_message_type(message_types=[message_type], partitions=partitions)
            mb_admin.set_message_type_expire(message_type,
                                            expire_time_ms=retention_period,
                                            data_limit_bytes=retention_size)
    def create_topics(self):
        """
        Create required messagebus topics for csm.
        """
        message_server_endpoints = Conf.get(const.CONSUMER_INDEX, const.KAFKA_ENDPOINTS)
        MessageBus.init(message_server_endpoints)
        mb_admin = MessageBusAdmin(admin_id = Conf.get(const.CSM_GLOBAL_INDEX,const.MSG_BUS_ADMIN_ID))
        self._create_perf_stat_topic(mb_admin)
        self._create_cluster_stop_topic(mb_admin)
