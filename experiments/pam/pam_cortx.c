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
PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv){
	return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv){
	pam_syslog(pamh, LOG_ERR, "Acc management is not supported\n");
	return PAM_SERVICE_ERR;
}

PAM_EXTERN int pam_sm_chauthtok(pam_handle_t *pamh, int flags, int argc, const char **argv){
	pam_syslog(pamh, LOG_ERR, "Password management is not supported\n");
	return PAM_SERVICE_ERR;
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv){
	pam_syslog(pamh, LOG_ERR, "Session management is not supported\n");
	return PAM_SERVICE_ERR;
}

PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv){
	pam_syslog(pamh, LOG_ERR, "Session management is not supported\n");
	return PAM_SERVICE_ERR;
}

static void curl_cleanup(struct curl_slist *headers, CURL *pCurl){
	curl_slist_free_all(headers);
	curl_easy_cleanup(pCurl);
}

static int login(pam_handle_t *pamh, const char *pUsername, const char *pPassword){
    //Login Function for CSM/S3 users
	const char *pUrl = "http://localhost:28101/api/v2/login";
	CURL *pCurl = NULL;
	struct curl_slist *headers = NULL;
	int res = -1;
	char body_file_name[100] = "/tmp/response_body_";
	char header_file_name[100] = "/tmp/response_headers_";
	FILE *header_file = NULL;
	FILE *body_file = NULL;

	strcat(header_file_name,pUsername);
	strcat(body_file_name,pUsername);
	pam_syslog(pamh, LOG_INFO, "Login to CORTX... Username: %s\n", pUsername);
	pCurl = curl_easy_init();

	if (!pCurl){
		pam_syslog(pamh, LOG_ERR, "Can't initialize curl.\n");
		curl_cleanup(headers, pCurl);
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
		curl_cleanup(headers, pCurl);
		return -1;
	}

	/* create json object for post */
	json_object *jobj = json_object_new_object();
	json_object_object_add(jobj, "username", json_object_new_string(pUsername));
	json_object_object_add(jobj, "password", json_object_new_string(pPassword));

	/* set curl options */
	if(curl_easy_setopt(pCurl, CURLOPT_URL, pUrl)!=CURLE_OK){
		curl_cleanup(headers, pCurl);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_FAILONERROR, TRUE)!=CURLE_OK){
		curl_cleanup(headers, pCurl);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_CUSTOMREQUEST, "POST")!=CURLE_OK){
		curl_cleanup(headers, pCurl);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_HTTPHEADER, headers)!=CURLE_OK){
		curl_cleanup(headers, pCurl);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_POSTFIELDS, json_object_to_json_string(jobj))!=CURLE_OK){
		curl_cleanup(headers, pCurl);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_TIMEOUT, 10L)!=CURLE_OK){
		curl_cleanup(headers, pCurl);
		return -1;
	}
	header_file = fopen(header_file_name, "wb");
	if (!header_file){
		curl_cleanup(headers,pCurl);
		pam_syslog(pamh, LOG_ERR, "Response Header File Not Opened\n");
		return -1;
	}
	body_file = fopen(body_file_name, "wb");
	if (!body_file){
		curl_cleanup(headers,pCurl);
		pam_syslog(pamh, LOG_ERR, "Response Body File Not Opened\n");
		fclose(header_file);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_HEADERDATA, header_file)!=CURLE_OK){
		curl_cleanup(headers,pCurl);
		fclose(header_file);
		fclose(body_file);
		return -1;
	}
	if(curl_easy_setopt(pCurl, CURLOPT_WRITEDATA, body_file)!=CURLE_OK){
		curl_cleanup(headers,pCurl);
		fclose(header_file);
		fclose(body_file);
		return -1;
	}
	res = curl_easy_perform(pCurl);
	fclose(header_file);
	fclose(body_file);
	curl_cleanup(headers, pCurl);

	if (res != 0){
		remove(header_file_name);
		pam_syslog(pamh, LOG_ERR, "Login to CORTX Failed\n");
	}
	else{
		pam_syslog(pamh, LOG_INFO, "Login to CORTX Successful\n");
	}
	remove(body_file_name);
	pam_syslog(pamh, LOG_INFO, "CURL Response code: %d\n", res);
	return res;
}

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv){
    //PAM Function which is initialized whenever Login Mechanism is called.
	int ret = 0;
	const char *pUsername = NULL;
	const char *pPassword = NULL;

	if (pam_get_user(pamh, &pUsername, NULL) != PAM_SUCCESS || pUsername == NULL || *pUsername == '\0'){
		pam_syslog(pamh, LOG_ERR, "Error in Fetching Username.\n");
		return PAM_AUTH_ERR;
	}

	if (pam_get_authtok(pamh, PAM_AUTHTOK, &pPassword , NULL) != PAM_SUCCESS || pPassword == NULL || *pPassword == '\0'){
		pam_syslog(pamh, LOG_ERR, "Error in Fetching Password.\n");
		return PAM_AUTH_ERR;
	}

	ret = PAM_SUCCESS;

	if (login(pamh, pUsername, pPassword) != 0){
		ret = PAM_AUTH_ERR;
	}
	return ret;
}
