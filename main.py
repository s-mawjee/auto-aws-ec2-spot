import boto3
from time import sleep
import configparser
import os
import socket
import sys


# import json
# from datetime import date, datetime


# def json_serial(obj):
#     """JSON serializer for objects not serializable by default json code"""

#     if isinstance(obj, (datetime, date)):
#         return obj.isoformat()
#     raise TypeError("Type %s not serializable" % type(obj))


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
#     client = EC2Connection(config.get('IAM', 'access'),
#                            config.get('IAM', 'secret'))
#     regions = client.get_all_regions()
#     for r in regions:
#         if r.name == config.get('EC2', 'region'):
#             client = EC2Connection(config.get(
#                 'IAM', 'access'), config.get('IAM', 'secret'), region=r)
#             return client
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
        Filters=[
            {
                'Name': 'image-id',
                'Values': [config.get('EC2', 'ami')]
            }
        ])
    reservations = response['Reservations']
    if len(reservations) > 0:
        r_instances = [
            inst for resv in reservations for inst in resv['Instances']]
        for inst in r_instances:
            print("Instance Id: %s (%s)" %
                  (inst['InstanceId'], inst['State']['Name']))


def get_spot_price(client):
    price_history = client.describe_spot_price_history(MaxResults=10,
                                                       InstanceTypes=[
                                                           config.get('EC2', 'type')],
                                                       ProductDescriptions=[config.get('EC2', 'product_description')])
    # with open('data.json', 'w') as outfile:
    #     json.dump(price_history['SpotPriceHistory'],
    #               outfile, default=json_serial)

    return float(price_history['SpotPriceHistory'][0]['SpotPrice'])


def provision_instance(client, user_data):
    req = client.request_spot_instances(InstanceCount=1,
                                        Type='one-time',
                                        InstanceInterruptionBehavior='terminate',
                                        LaunchSpecification={
                                            # 'SecurityGroups': [
                                            #     config.get(
                                            #         'EC2', 'security_group')
                                            # ],
                                            'ImageId': config.get('EC2', 'ami'),
                                            'InstanceType': config.get('EC2', 'type'),
                                            'KeyName': config.get('EC2', 'key_pair'),

                                            'UserData': user_data
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
        # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if inst['PublicIpAddress'] is None:
            inst = get_existing_instance_by_tag(client)
        try:
            if inst['PublicIpAddress'] is None:
                print('IP not assigned yet ...')
            else:
                # s.connect((inst['PublicIpAddress'], 22))
                # s.shutdown(2)
                print('Server is up!')
                print('Server Public IP - %s' % inst['PublicIpAddress'])
                break
        except:
            print('Waiting...', sleep(10))


def main():
    # Entry
    action = 'list' if len(sys.argv) == 1 else sys.argv[1]
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
        print('Active Spot Instnaces (AMI: %s)' % config.get('EC2', 'ami'))
        list_all_existing_instances(client)
    else:
        print('No action taken')


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('ec2-spot-instance-config.cfg')
    main()
