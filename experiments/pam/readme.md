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
