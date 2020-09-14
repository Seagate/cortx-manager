# CORTX-Manager Quick Start Guide

This guide provides a step-by-step walkthrough for getting you CORTX-Manager ready.

- [1.0 Prerequisites](##10-Prerequisites)
- [1.2 Install Cortx Manager](#12-Install-Cortx-Manager)
- [1.3 Deploy CORTX-Manager on Test VM](#13-Deploy-CORTX-Manager-on-Test-VM)

## 1.0 Prerequisites

<details>
<summary>Before you begin</summary>
<p>

1. Login with super user:
   
   `$ sudo su`

    Or 
    
    `$ sudo -s`

2. Ensure you've installed the following softwares:

   1. Install RabbitMQ
      
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

        ![virtual host](../dev/images/Image 1.jpg)

     3. Navigate to the Admin section.
        
        ![Admin section](..dev/images/Image 2.jpg)

     4. Click on add user and enter the following details:
        
        > **username:** sspluser 

        > **password:** sspl4ever
        
    5. Added user will be listed in users table. Click on added user.
      
       ![Added user](../dev/images/Image 3.jpg)
    
    6. Set all permissions and select virtual host as SSPL
       
       ![User permissions](../dev/images/Image 4.jpg)

  3. Install Elastic Search:
  
     ```shell

     $ yum install -y https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-7.3.2-x86_64.rpm
     $ vim /etc/elasticsearch/elasticsearch.yml       
     $ systemctl enable elasticsearch
     $ systemctl start elasticsearch
     ```
    
   ![Successful elasticsearch.yml installation](../dev/images/Image 5.jpg)

  4. Install Consul
  
     1. Download consule binary. 
     
        `$ wget https://releases.hashicorp.com/consul/1.8.3/consul_1.8.3_linux_amd64.zip`

     2. Unzip downloaded zip.
     
        `$ unzip consul_1.8.3_linux_amd64.zip`

     3. Install unzip if not already installed.
     
        `$ yum install unzip`

        `$ unzip consul_1.8.3_linux_amd64.zip`

     4. Move binary to /usr/loval/bin folder.
     
        `$ mv consul /usr/local/bin/`

     5. Check if the PATH contains `/usr/local/bin`. If it doesn’t, add it to the path.
        
        ```shell 
        $ echo $PATH
        $ export PATH=$PATH:/usr/local/bin
        ```
     6. Check if consul is installed.
     
        `$ consul`
     7. Run consul in the background.
     
        `$ nohup consul agent --dev &`

  5. Install Python 3
  
     `$ yum –y install python3`
     
  6. Install GitHub.
     
     Refer to the [Contributing to CORTX Manager](ContributingToCortxManager.md) document to install GitHub and clone cortx-manager and its dependent repos.

  7. Install pyutils that is custom-built for CORTX project:
  
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
  8. Install provisioner
  
     1. Go to your home directory.
     2. Git clone the provisioner repository, and follow the steps below:
    
        ```shell
        $ git clone git@github.com:Seagate/cortx-prvsnr.git
        $ mkdir /opt/seagate/cortx/provisioner
        $ ln -s /<path-to-cortx-prvsnr>/cortx-prvsnr/* /opt/seagate/cortx/provisioner/
       ```
       
</p>
</details>

## 1.2 Install Cortx Manager

 The cortx-manager repository is available at https://github.com/Seagate/cortx-csm-agent
 
 1. Clone cortx-manager using HTTP or SSH:
 
    ```shell
    
    $ git clone https://github.com/Seagate/cortx-csm-agent.git
    $ git clone git@github.com:Seagate/cortx-csm-agent.git
    ```
 2. Once you have obtained the sources, build the cortx-manager by running: 
 
    ```shell
    
    $ cd cortx-cortx-manager
    $ sudo cicd/build.sh
    ```
 3. Run `sudo cicd/build.sh -h` to list build options in more detail. 
 
    **Examples:**
     
     - To build cortx-manager with integration tests, run: `sudo cicd/build.sh -i`
     - To build cortx-manager with log level debug, run: `sudo cicd/build.sh -q true`
     
 4. Prepare your environment by deploying CORTX on your system. Refer to [Auto-deployment of VM](https://github.com/Seagate/cortx-prvsnr/wiki/Deployment-on-VM_Auto-Deploy)

## 1.3 Deploy CORTX-Manager on Test VM

All the dependencies should be preinstalled and prerequisites met before you run the CORTX-Manager. Follow these steps:

   1. SSH-Login to VM with GitHub ID and Password.
   2. Remove previously installed CORTX-Manager RPMs, if any:

        For pkg in 
        
        `rpm -qa | grep -E "cortx|salt"` 
        
        Run 
        
        `yum remove -y $pkg`

   3. Install CORTX-Manager [RPM](http://cortx-storage.colo.seagate.com/releases/cortx/components/dev/multibranch/cortx-manager/) using:
  
     ```shell
     
     yum install -i <cortx-manager-rpm-link>
     
   4. Executing the cortx-manager setup commands should pass: 
  
     ```shell
     
     csm_setup post_install
     csm_setup config
     csm_setup init
     ```
  5. Enable and Restart cortx-manager usig: 
     
     ```shell

     systemctl enable cortx_manager
     systemctl restart cortx_manager
     ```

## You're All Set & You're Awesome!

We thank you for stopping by to check out the CORTX Community. We are fully dedicated to our mission to build open source technologies that help the world save unlimited data and solve challenging data problems. Join our mission to help reinvent a data-driven world. 

### Contribute to CORTX Manager

Please contribute to the [CORTX Open Source project](https://github.com/Seagate/cortx/blob/main/doc/SuggestedContributions.md) and join our movement to make data storage better, efficient, and more accessible.

Refer to our [CORTX Community Guide](https://github.com/Seagate/cortx/blob/main/doc/CORTXContributionGuide.md) to get started with your first contribution.

### Reach Out to Us

You can reach out to us with your questions, feedback, and comments through our CORTX Communication Channels:

- Join our CORTX-Open Source Slack Channel to interact with your fellow community members and gets your questions answered. [![Slack Channel](https://img.shields.io/badge/chat-on%20Slack-blue)](https://join.slack.com/t/cortxcommunity/shared_invite/zt-femhm3zm-yiCs5V9NBxh89a_709FFXQ?)
- If you'd like to contact us directly, drop us a mail at cortx-questions@seagate.com.
