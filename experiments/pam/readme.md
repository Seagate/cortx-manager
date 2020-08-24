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

* **pam-devel**
	* sudo  yum install pam-devel
* **curl-devel**
	* sudo yum install curl-devel
* **jason-c-devel**
	* sudo yum install json-c-devel

### **Make PAM FIle **
    * gcc -fPIC -c pam.c
    * gcc -shared -o pam_csm.so pam.o -lpam  -lcurl -ljson-c


### **Configuration**
   
   1.  add the following line in /etc/pam.d/sshd at starting.
   ```
   auth       optional   pam_csm.so
   ```
   2.  Add the Following Configuration in /etc/pam.d/system-auth-ac
   ```
   auth       optional  pam_csm.so
   ```
   3.
   /etc/pam.d/password-auth 
   ```
   auth        sufficient   pam_csm.so
   account     sufficient   pam_csm.so
   password    sufficient    pam_csm.so 
   ```
