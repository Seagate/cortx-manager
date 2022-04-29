# CORTX-Manager Quick Start Guide

This guide provides a step-by-step walkthrough for getting you CORTX-Manager ready.

-   [1.0 Prerequisites](##10-Prerequisites)
-   [1.2 Install Cortx Manager](#12-Install-Cortx-Manager)
-   [1.3 Deploy CORTX-Manager on Test VM](#13-Deploy-CORTX-Manager-on-Test-VM)

## 1.0 Prerequisites

<details>
<summary>Before you begin</summary>
<p>
   
   <details>
   <summary>Click to view the process to manually install the full stack.</summary>
   <p>

1.  You'll need to install the following components:

-   [Provisioner](https://github.com/Seagate/cortx-prvsnr/blob/dev/Cortx-ProvisionerQuickstartGuide.md)
-   [S3 Server](https://github.com/Seagate/cortx-s3server/blob/dev/docs/CORTX-S3%20Server%20Quick%20Start%20Guide.md)
-   [Hare](https://github.com/Seagate/cortx-hare)
-   [Monitor](https://github.com/Seagate/cortx-monitor/blob/dev/cortx-monitorQuickstartGuide.md)

2.  Login with super user:
   
   `$ sudo su`

   Or 
    
   `$ sudo -s`

3.  Ensure you've installed the following softwares:
  
  1.  Install RabbitMQ
      
      ```shell
      $ wget https://www.rabbitmq.com/releases/rabbitmq-server/v3.6.1/rabbitmq-server-3.6.1-1.noarch.rpm
      $ rpm --import https://www.rabbitmq.com/rabbitmq-release-signing-key.asc
      $ yum install rabbitmq-server-3.6.1-1.noarch.rpm
      $ systemctl enable rabbitmq-server
      $ systemctl start rabbitmq-server
      $ rabbitmqctl add_user admin password
      $ rabbitmqctl set_user_tags admin administrator
      $ rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"
      $ rabbitmqctl add_vhost SSPL
      $ rabbitmq-plugins enable rabbitmq_management

     From your browser, navigate go to: http://<hostname>:15672/ 

     1. Login with your admin password.
     2. Select Virtual host as SSPL.
     
        ![](images/Image%201.jpg)
     3. Navigate to the Admin section.
        
        ![](images/Image%202.jpg)
     4. Click on add user and enter the following details:
        
        > **username:** sspluser 

        > **password:** sspl4ever
        
     5. Added user will be listed in users table. Click on added user.
      
        ![](images/Image%203.jpg)
     6. Set all permissions and select virtual host as SSPL
       
        ![](images/Image%204.jpg)
  2. Install Elastic Search:
  
     ```shell

     $ yum install -y https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-7.3.2-x86_64.rpm
     $ vim /etc/elasticsearch/elasticsearch.yml       
     $ systemctl enable elasticsearch
     $ systemctl start elasticsearch
     ```
    
     ![Successful elasticsearch.yml installation](images/Image-5.jpg)

  3. Install Consul
  
     1.  Download consule binary. 
     
        `$ wget https://releases.hashicorp.com/consul/1.8.3/consul_1.8.3_linux_amd64.zip`

     2.  Unzip downloaded zip.
     
        `$ unzip consul_1.8.3_linux_amd64.zip`

     3.  Install unzip if not already installed.
     
        `$ yum install unzip`

        `$ unzip consul_1.8.3_linux_amd64.zip`

     4.  Move binary to /usr/loval/bin folder.
     
        `$ mv consul /usr/local/bin/`

     5.  Check if the PATH contains `/usr/local/bin`. If it doesn’t, add it to the path.
        
        ```shell
        
        $ echo $PATH
        $ export PATH=$PATH:/usr/local/bin
        ```
     6.  Check if consul is installed.
     
        `$ consul`
        
     7.  Run consul in the background.
     
        `$ nohup consul agent --dev &`

  4. Install provisioner
  
     1.  Go to your home directory.
     2.  Git clone the provisioner repository, and follow the steps below:
     
      ```shell
         $ git clone git@github.com:Seagate/cortx-prvsnr.git
         $ mkdir /opt/seagate/cortx/provisioner
         $ ln -s /<path-to-cortx-prvsnr>/cortx-prvsnr/* /opt/seagate/cortx/provisioner/
      ```
      </p>
      </details>
      
     <details>
   <summary>Install OVA and these prerequisites to skip manual installation.</summary>
   <p>
      
  Please refer to the documentation to [Import the CORTX Open Virtual Appliance (OVA)](https://github.com/Seagate/cortx/blob/main/doc/Importing_OVA_File.rst).
     
  1. Install GitHub.
     
     Refer to the [CORTX Contribution Guide](https://github.com/Seagate/cortx/blob/main/CONTRIBUTING.md) document to install GitHub and clone cortx-manager and its dependent repos.

  2. Install pyutils that is custom-built for CORTX project:
  
     1. Go to your home directory
     2. Git clone `cortx-py-utils` and follow the steps below:
     
        ```shell

        $ cd /home/727891/githubssh/
        $ git clone --recursive git@github.com:Seagate/cortx-py-utils.git
        $ cd /opt/seagate/
        $ mkdir cortx
        $ cd cortx
        $ ln -s /<path-to-cortx-py-utils>/cortx-py-utils/src/utils
        ```
  3. Install Python 3
  
     `$ yum –y install python3`
     
   </p>
   </details>
      
</p>
</details>

## 1.2 Install Cortx-Manager

 Click [here](https://github.com/Seagate/cortx-manager) to navigate to the cortx-manager repository. 
 
 <details>
   <summary>Follow these steps to Install CORTX-Manager</summary>
   <p>
 
1.  Clone cortx-manager using HTTP or SSH:
 
    ```shell
    
    $ git clone https://github.com/Seagate/cortx-manager.git
    $ git clone git@github.com:Seagate/cortx-manager.git
    ```
2.  Once you have obtained the sources, build the cortx-manager by running: 
 
    ```shell
    
    $ cd cortx-cortx-manager
    $ sudo cicd/build.sh
    ```
3.  Run `$ sudo cicd/build.sh -h` to list build options in more detail. - This will build an RPM on a dest directory.
 
   **Examples:**
     
     -   To build cortx-manager with integration tests, run: `$ sudo cicd/build.sh -i`
     -   To build cortx-manager with log level debug, run: `$ sudo cicd/build.sh -q true`
     
     </p>
     </details>
     
## 1.3 Deploy CORTX-Manager on Test VM

All the dependencies should be preinstalled and prerequisites met before you run the CORTX-Manager. 

<details>
   <summary>Follow these steps to deploy the CORTX-Manager on a Test VM</summary>
   <p>

1.  SSH-Login to VM with GitHub ID and Password.
2.  Remove previously installed CORTX-Manager RPMs, if any:

      For pkg in 
      
      `$ rpm -qa | grep -E "cortx|salt"` 
      
      Run 
      
      `$ yum remove -y $pkg`

3.  Install CORTX-Manager (RPM) using:

   ```shell
   
      $ yum install -i <rpm-created-by-dest-directory>
      
   ```
   
4.  Executing the cortx-manager setup commands should pass: 

   ```shell
   
   $ cortx-manager_setup post_install
   $ cortx-manager_setup config
   $ cortx-manager_setup init
   ```
5.  Enable and Restart cortx-manager using: 
   
   ```shell

   $ systemctl enable cortx_manager
   $ systemctl restart cortx_manager
   ```
   
   </p>
   </details>
     

## You're All Set & You're Awesome

We thank you for stopping by to check out the CORTX Community. We are fully dedicated to our mission to build open source technologies that help the world save unlimited data and solve challenging data problems. Join our mission to help reinvent a data-driven world. 

### Contribute to CORTX Manager

Please contribute to the [CORTX Open Source project](https://github.com/Seagate/cortx/blob/main/doc/SuggestedContributions.md) and join our movement to make data storage better, efficient, and more accessible.

Refer to our [CORTX Contribution Guide](CONTRIBUTING.md) to get started with your first contribution.

### Reach Out to Us

Please refer to the [Support](SUPPORT.md) document to know the various communication channels for reaching out to us.
