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

/* These #defines must be present according to PAM documentation. */
#define PAM_SM_AUTH
#define PAM_SM_ACCOUNT
#define PAM_SM_SESSION
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

#ifndef PAM_EXTERN
#define PAM_EXTERN
#endif

/* expected hook */
PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
	return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
	return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_chauthtok(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
	return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
	return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
	return PAM_SUCCESS;
}

static void curl_cleanup(struct curl_slist *headers, CURL *pCurl){
	/* free the list */
	curl_slist_free_all(headers);
	/* cleanup the CURL */
	curl_easy_cleanup(pCurl);
}

static int login(pam_handle_t *pamh, const char *pUsername, const char *pPassword)
{
    //Login Function for CSM Initialization.
	pam_syslog(pamh, LOG_INFO, "Using Username %s", pUsername);
	static const char *pUrl = "http://localhost:28101/api/v1/login";
	CURL *pCurl = curl_easy_init();
	struct curl_slist *headers = NULL;
	int res = -1;
	static const char *header_file_name = "/etc/csm/response_headers.out";
	FILE *header_file = NULL;
	static const char *body_file_name = "/etc/csm/response_body.out";
	FILE *body_file = NULL;
	pam_syslog(pamh, LOG_INFO, "URL- %s \n", pUrl);
	if (!pCurl)
	{
		return -1;
	}

	/* set content type */
	headers = curl_slist_append(headers, "Accept: application/json");
	if (headers == NULL){
		curl_cleanup(headers,pCurl);
		return -1;
	}	
	headers = curl_slist_append(headers, "Content-Type: application/json");
	if (headers == NULL){
		curl_cleanup(headers,pCurl);
		return -1;
	}

	/* create json object for post */
	json_object *jobj = json_object_new_object();
	json_object_object_add(jobj, "username", json_object_new_string(pUsername));
	json_object_object_add(jobj, "password", json_object_new_string(pPassword));

	/* set curl options */
	if(curl_easy_setopt(pCurl, CURLOPT_URL, pUrl)!=CURLE_OK){
		curl_cleanup(headers,pCurl);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_FAILONERROR, TRUE)!=CURLE_OK){
		curl_cleanup(headers,pCurl);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_CUSTOMREQUEST, "POST")!=CURLE_OK){
		curl_cleanup(headers,pCurl);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_HTTPHEADER, headers)!=CURLE_OK){
		curl_cleanup(headers,pCurl);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_POSTFIELDS, json_object_to_json_string(jobj))!=CURLE_OK){
		curl_cleanup(headers,pCurl);
		return -1;
	}

	/* open the header file */
	header_file = fopen(header_file_name, "wb");
	if (!header_file)
	{
		curl_cleanup(headers,pCurl);
		pam_syslog(pamh, LOG_ERR, "Response Header File Not Opened\n");
		return -1;
	}
	/* open the body file */
	body_file = fopen(body_file_name, "wb");
	if (!body_file)
	{
		curl_cleanup(headers,pCurl);
		pam_syslog(pamh, LOG_ERR, "Response Body File Not Opened\n");
		fclose(header_file);
		return -1;
	}
	/* we want the headers be written to this file handle */
	if(curl_easy_setopt(pCurl, CURLOPT_HEADERDATA, header_file)!=CURLE_OK){
		curl_cleanup(headers,pCurl);
		return -1;
	}
	/* we want the body be written to this file handle instead of stdout */
	if(curl_easy_setopt(pCurl, CURLOPT_WRITEDATA, body_file)!=CURLE_OK){
		curl_cleanup(headers,pCurl);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_TIMEOUT, 1)!=CURLE_OK){
		curl_cleanup(headers,pCurl);
		return -1;
	}
	res = curl_easy_perform(pCurl);
	curl_cleanup(headers,pCurl);
	/* close the files */
	fclose(header_file);
	fclose(body_file);

	if (res != 0)
	{
		pam_syslog(pamh, LOG_ERR, "Login to CSM Failed\n");
	}
	else
	{
		pam_syslog(pamh, LOG_INFO, "Login to CSM Successful\n");
	}
	pam_syslog(pamh, LOG_INFO, "CURL Response code: %d\n", res);
	return res;
}

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
    //PAM Function which is initialized whenever Login Mechanism is called.
	pam_syslog(pamh, LOG_INFO, "Logging In With CSM User.\n");
	int ret = 0;
	const char *pUsername = NULL;
	const char *pPassword = NULL;

	if (pam_get_user(pamh, &pUsername, NULL) != PAM_SUCCESS || pUsername == NULL || *pUsername == '\0')
	{
		pam_syslog(pamh, LOG_ERR, "Error in Fetching Username.\n");
		return PAM_AUTH_ERR;
	}

	if (pam_get_authtok(pamh, PAM_AUTHTOK, &pPassword , NULL) != PAM_SUCCESS || pPassword == NULL || *pPassword == '\0')
	{
		pam_syslog(pamh, LOG_ERR, "Error in Fetching Password.\n");
		return PAM_AUTH_ERR;
	}

	ret = PAM_SUCCESS;
	if (login(pamh, pUsername, pPassword) != 0)
	{
		ret = PAM_AUTH_ERR;
	}
	return ret;
}
