// CORTX-CSM: CORTX Management web and CLI interface.
// Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.
// For any questions about this software or licensing,
// please email opensource@seagate.com or cortx-questions@seagate.com.

#define PAM_SM_AUTH
#define PAM_SM_PASSWORD

// standard stuff
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <syslog.h>
// pam stuff
#include <security/pam_modules.h>
#include <security/pam_ext.h>
// libcurl
#include <curl/curl.h>
// libjson
#include <json-c/json.h>

/* expected hook */
PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
	pam_syslog(pamh, LOG_INFO, "Initialized SM SetCredentials\n");
	return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
	pam_syslog(pamh, LOG_INFO, "Initialized SM Acc Management\n");
	return PAM_SUCCESS;
}
PAM_EXTERN int pam_sm_chauthtok(pam_handle_t *pamh, int flags, int argc, const char **argv){
pam_syslog(pamh, LOG_INFO, "Initialized CHAAUTOK\n");
	return PAM_SUCCESS;
}
static int login(pam_handle_t *pamh, const char *pUsername, const char *pPassword)
{
    //Login Function for CSM Initialization.
	pam_syslog(pamh, LOG_INFO, "Verify CSM User %s \n", pUsername);
	const char *pUrl = "http://localhost:8101/api/v1/login?debug";
	CURL *pCurl = curl_easy_init();
	struct curl_slist *headers = NULL;
	int res = -1;
	static const char *header_file_name = "/var/log/response_headers.out";
	FILE *header_file;
	static const char *body_file_name = "/var/log/response_body.out";
	FILE *body_file;
	pam_syslog(pamh, LOG_ERR, "URL- %s \n", pUrl);
	if (!pCurl)
	{
		return -1;
	}
	/* set content type */
	headers = curl_slist_append(headers, "Accept: application/json");
	headers = curl_slist_append(headers, "Content-Type: application/json");
	/* create json object for post */
	json_object *jobj = json_object_new_object();
	pam_syslog(pamh, LOG_DEBUG, "Using Username %s", pUsername);
	json_object_object_add(jobj, "username", json_object_new_string(pUsername));
	json_object_object_add(jobj, "password", json_object_new_string(pPassword));
	/* set curl options */
	curl_easy_setopt(pCurl, CURLOPT_URL, pUrl);
	curl_easy_setopt(pCurl, CURLOPT_CUSTOMREQUEST, "POST");
	curl_easy_setopt(pCurl, CURLOPT_HTTPHEADER, headers);
	curl_easy_setopt(pCurl, CURLOPT_POSTFIELDS, json_object_to_json_string(jobj));
	/* Write Output */
	header_file = fopen(header_file_name, "wb");
	if (!header_file)
	{
		curl_easy_cleanup(pCurl);
		pam_syslog(pamh, LOG_INFO, "Response Header File Not Opened");
		return -1;
	}

	/* open the body file */
	body_file = fopen(body_file_name, "wb");
	if (!body_file)
	{
		curl_easy_cleanup(pCurl);
		pam_syslog(pamh, LOG_INFO, "Response Body File Not Opened");
		fclose(header_file);
		return -1;
	}

	/* we want the headers be written to this file handle */
	curl_easy_setopt(pCurl, CURLOPT_HEADERDATA, headerfile);

	/* we want the body be written to this file handle instead of stdout */
	curl_easy_setopt(pCurl, CURLOPT_WRITEDATA, bodyfile);
	curl_easy_setopt(pCurl, CURLOPT_TIMEOUT, 1);
	res = curl_easy_perform(pCurl);
	curl_easy_cleanup(pCurl);
	pam_syslog(pamh, LOG_ERR, "Res: %d\n", res);
	if (res != 0)
	{
		pam_syslog(pamh, LOG_ERR, " Login to CSM Failed Returned Response Code: %d\n", res);
	}
	else
	{
		pam_syslog(pamh, LOG_INFO, " Login to CSM Successful Status Code: %d\n", res);
	}
	/* close the files */
	fclose(header_file);
	fclose(body_file);
	return res;
}

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
    //PAM Function which is initialized whenever Login Mechanism is called.
	pam_syslog(pamh, LOG_INFO, "Logging In With CSM User.\n");
	int ret = 0;
	const char *pUsername = NULL;
	struct pam_message msg;
	struct pam_conv *pItem;
	struct pam_response *pResp;
	const struct pam_message *pMsg = &msg;

	msg.msg_style = PAM_PROMPT_ECHO_OFF;
	if (pam_get_user(pamh, &pUsername, NULL) != PAM_SUCCESS)
	{
		pam_syslog(pamh, LOG_ERR, "Error in Fetching Username.\n");
		return PAM_AUTH_ERR;
	}

	if (pam_get_item(pamh, PAM_CONV, (const void **)&pItem) != PAM_SUCCESS || !pItem)
	{
		pam_syslog(pamh, LOG_ERR, "Error in Fetching Pam Conversation Pointer.\n");
		return PAM_AUTH_ERR;
	}
	memset(pResp, 0, sizeof(struct pam_response));
	pItem->conv(1, &pMsg, &pResp, pItem->appdata_ptr);
	ret = PAM_SUCCESS;
	if (login(pamh, pUsername, pResp[0].resp) != 0)
	{
		ret = PAM_AUTH_ERR;
	}
	memset(pResp[0].resp, 0, strlen(pResp[0].resp));
	free(pResp);
	return ret;
}
