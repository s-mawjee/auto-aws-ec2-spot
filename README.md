# auto-aws-ec2-spot

A Python script that requests a spot EC2 instance. Using tag name to control specific instance.

## Prerequisites

* Python 3
* [Boto 3](https://boto3.readthedocs.io/en/latest/)
* [AWS CLI](https://aws.amazon.com/cli/)

## Setup

### Boto 3 [Install](https://boto3.readthedocs.io/en/latest/guide/quickstart.html#installation)

<pre>
$ pip install boto3
</pre>

### AWS CLI Configure

* Create Access Key for Your AWS Account. Instructions can be found at https://docs.aws.amazon.com/general/latest/gr/managing-aws-access-keys.html

* Configure AWS CLI using AWS Access Key ID and AWS Secret Access Key
  * <pre>$ aws configure</pre>
  * <pre>AWS Access Key ID [None]: 'ACCESS_KEY_ID'
    AWS Secret Access Key [None]: 'SECRET_ACCESS_KEY'
    Default region name [None]:'Region'
    Default output format [None]: ENTER</pre>

## Configuration File

List of a configure fields

* `tag`: A tag that will be used by the script to identify the instance
* `ami`: AMI_ID - Get the appropriate AMI ID for your region from http://aws.amazon.com/amazon-linux-ami/
* `key_pair`: Named keypair on EC2 for instance creation
* `security_group`: Named security_group on EC2 for instance creation
* `max_bid`: Max bid price for spot instance. Current bid prices can be found at https://aws.amazon.com/ec2/spot/pricing/
* `type`: Type of EC2 instance. List can be found at https://aws.amazon.com/ec2/instance-types/
* `region`: Region code (eg. 'us-west-1'). List of regions can be found at https://docs.aws.amazon.com/general/latest/gr/rande.html#ec2_region
* `product_description`: 'Linux/UNIX' or 'Windows'
* `user_data` User data be passed by the script to instance
* `user_data_file` Script would read the file content, and pass data to instance as user-data

\*Refer to `example-config.cfg` file.

## Request EC2 Spot Instance

<pre>python main.py start CONFIG_FILE_NAME.cfg</pre>

## Terminate EC2 Spot Instance

<pre>python main.py stop CONFIG_FILE_NAME.cfg</pre>

## List EC2 Instances

<pre>python main.py list CONFIG_FILE_NAME.cfg</pre>
