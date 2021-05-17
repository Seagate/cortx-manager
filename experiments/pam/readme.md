<!--
CORTX-CSM: CORTX Management web and CLI interface.
Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.
You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
For any questions about this software or licensing,
please email opensource@seagate.com or cortx-questions@seagate.com.
-->
# **PAM Authentication Integration Documentation**

#### **Required Packages.**

* **gcc**
    * sudo yum install gcc
* **pam-devel**
	* sudo  yum install pam-devel
* **curl-devel**
	* sudo yum install curl-devel
* **jason-c-devel**
	* sudo yum install json-c-devel

### **Make PAM FIle **
    * gcc -fPIC -c pam_cortx.c
    * gcc -shared -o pam_cortx.so pam_cortx.o -lpam  -lcurl -ljson-c


### **Configuration**

   1.  copy pam_cortx.so to /lib64/security/

   2.  add the following line in /etc/pam.d/password-auth
   ```
   auth        sufficient    pam_cortx.so   try_first_pass
   account     sufficient    pam_cortx.so
   password    sufficient    pam_cortx.so 
   ```
