import boto3
from time import sleep
import configparser
import socket
import sys
import base64


def read_user_data_from_local_config():
    user_data = config.get('EC2', 'user_data')
    if config.get('EC2', 'user_data') is None or user_data == '':
        try:
            user_data = (open(config.get('EC2', 'user_data_file'), 'r')).read()
        except:
            user_data = ''
    return user_data


def create_client():
    client = boto3.client('ec2')
    return client


def get_existing_instance_by_tag(client):
    response = client.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [config.get('EC2', 'tag')]
            }
        ])

    if len(response['Reservations']) > 0:
        return response['Reservations'][0]['Instances'][0]
    else:
        return None


def list_all_existing_instances(client):
    response = client.describe_instances(
        # Filters=[
        #     {
        #         'Name': 'image-id',
        #         'Values': [config.get('EC2', 'ami')]
        #     }
        #]
    )
    reservations = response['Reservations']
    if len(reservations) > 0:
        r_instances = [
            inst for resv in reservations for inst in resv['Instances']]
        for inst in r_instances:
            print("Instance Id: %s | %s | %s" %
                  (inst['InstanceId'], inst['InstanceType'], inst['State']['Name']))


def get_spot_price(client):
    price_history = client.describe_spot_price_history(MaxResults=10,
                                                       InstanceTypes=[
                                                           config.get('EC2', 'type')],
                                                       ProductDescriptions=[config.get('EC2', 'product_description')])
    return float(price_history['SpotPriceHistory'][0]['SpotPrice'])


def provision_instance(client, user_data):
    user_data_encode = (base64.b64encode(user_data.encode())).decode("utf-8") 
    req = client.request_spot_instances(InstanceCount=1,
                                        Type='one-time',
                                        InstanceInterruptionBehavior='terminate',
                                        LaunchSpecification={
                                            'SecurityGroups': [
                                                config.get(
                                                    'EC2', 'security_group')
                                            ],
                                            'ImageId': config.get('EC2', 'ami'),
                                            'InstanceType': config.get('EC2', 'type'),
                                            'KeyName': config.get('EC2', 'key_pair'),

                                            'UserData': user_data_encode
                                        },
                                        SpotPrice=config.get('EC2', 'max_bid')
                                        )
    print('Spot request created, status: ' +
          req['SpotInstanceRequests'][0]['State'])

    print('Waiting for spot provisioning')
    while True:
        current_req = client.describe_spot_instance_requests(
            SpotInstanceRequestIds=[req['SpotInstanceRequests'][0]['SpotInstanceRequestId']])
        if current_req['SpotInstanceRequests'][0]['State'] == 'active':
            print('Instance allocated ,Id: ',
                  current_req['SpotInstanceRequests'][0]['InstanceId'])
            instance = client.describe_instances(InstanceIds=[current_req['SpotInstanceRequests'][0]['InstanceId']])[
                'Reservations'][0]['Instances'][0]
            client.create_tags(Resources=[current_req['SpotInstanceRequests'][0]['InstanceId']],
                               Tags=[{
                                   'Key': 'Name',
                                   'Value': config.get('EC2', 'tag')
                               }]
                               )
            return instance
        print('Waiting...',
              sleep(10))


def destroy_instance(client, inst):
    try:
        print('Terminating', inst['InstanceId'])
        client.terminate_instances(
            InstanceIds=[inst['InstanceId']])
        print('Termination complete (', inst['InstanceId'], ')')
        client.delete_tags(
            Resources=[
                inst['InstanceId']
            ],
            Tags=[
                {
                    'Key': 'Name',
                    'Value': config.get('EC2', 'tag')
                },
            ]
        )
    except:
        print('Failed to terminate:', sys.exc_info()[0])


def wait_for_up(client, inst):
    print('Waiting for instance to come up')
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if inst['PublicIpAddress'] is None:
            inst = get_existing_instance_by_tag(client)
        try:
            if inst['PublicIpAddress'] is None:
                print('IP not assigned yet ...')
            else:
                s.connect((inst['PublicIpAddress'], 22))
                s.shutdown(2)
                print('Server is up!')
                print('Server Public IP - %s' % inst['PublicIpAddress'])
                break
        except:
            print('Waiting...', sleep(10))

# def run_code(client, inst): 
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.connect((inst['PublicIpAddress'], 22))
#     s.



def main(action):
    client = create_client()
    if client is None:
        print('Unable to create EC2 client')
        sys.exit(0)
    inst = get_existing_instance_by_tag(client)
    user_data = read_user_data_from_local_config()

    if action == 'start':
        if inst is None or inst['State'] == 'terminated':
            spot_price = get_spot_price(client)
            print('Spot price is ', str(spot_price))
            if spot_price > float(config.get('EC2', 'max_bid')):
                print('Spot price is too high!')
                sys.exit(0)
            else:
                print('below maximum bid, continuing')
                provision_instance(client, user_data)
                inst = get_existing_instance_by_tag(client)
        wait_for_up(client, inst)
    elif action == 'stop' and inst is not None:
        destroy_instance(client, inst)
    elif action == 'list':
        print('EC2 Instnaces:')
        list_all_existing_instances(client)
    else:
        print('No action taken')


if __name__ == "__main__":

    action = 'list' if len(sys.argv) == 1 else sys.argv[1]
    config_file = ''
    if len(sys.argv) == 3:
        config_file = sys.argv[2]

    config = configparser.ConfigParser()
    config.read(config_file)
    main(action)
