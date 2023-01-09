import boto3
from . import utils

def cf_ls(get_all):
        client = boto3.client("cloudformation")
        ret = client.list_stacks()
        while "NextToken" in ret:
            for stack in ret["StackSummaries"]:
                if get_all or "araaliapicf." in stack["StackName"]:
                    if stack["StackStatus"] in ["DELETE_COMPLETE"]: continue
                    yield {"id": stack["StackId"], "name": stack["StackName"],
                            "created": stack["CreationTime"],
                            "status": stack["StackStatus"],
                            "drift": stack["DriftInformation"],
                            }
            ret = client.list_stacks(NextToken=ret["NextToken"])

def cf_rm(name):
    print("removing %s" % name)

def cf_add_vm():
    print("adding vm")

def cf_launch_fortified_vm(stack_name, email, key_pair, ami_id):
    if ami_id is None or ami_id == "":
        # Launch latest AmazonLinux AMI
        template_url = "https://s3.us-west-1.amazonaws.com/araalinetworks.test/quickstart_vm/AraaliVMQuickstartStack.template.json"
        return utils.run_command_logfailure(
            "aws cloudformation create-stack --stack-name %s --template-url %s\
            --parameters ParameterKey=KeyName,ParameterValue=%s ParameterKey=email,ParameterValue=%s" % (
            stack_name, template_url, key_pair, email)
        )
    else:
        # Use custom AMI ID (For internal usage)
        template_url = "https://s3.us-west-1.amazonaws.com/araalinetworks.test/quickstart_vm/AraaliVMQuickstartInternalStack.template.json"
        return utils.run_command_logfailure(
            "aws cloudformation create-stack --stack-name %s --template-url %s\
            --parameters ParameterKey=KeyName,ParameterValue=%s ParameterKey=email,ParameterValue=%s ParameterKey=AmiId,ParameterValue=%s" % (
            stack_name, template_url, key_pair, email, ami_id)
        )

def cf_launch_eks_cluster(stack_name, cluster_name, availability_zones):
    template_url = "https://s3.amazonaws.com/aws-quickstart/quickstart-amazon-eks/templates/amazon-eks-entrypoint-new-vpc.template.yaml"
    availability_zone_str = "\\\\,".join(availability_zones)
    return utils.run_command_logfailure(
       "aws cloudformation create-stack --stack-name %s --template-url %s --parameters ParameterKey=AvailabilityZones,ParameterValue=%s\
     ParameterKey=EKSClusterName,ParameterValue=%s ParameterKey=NumberOfAZs,ParameterValue=%s ParameterKey=EKSPublicAccessEndpoint,ParameterValue=Enabled --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND" % (
        stack_name, template_url, availability_zone_str, cluster_name, len(availability_zones))
    )

def cf_validate_stack_creation(stack_name):
    cf_client = boto3.client('cloudformation')
    cf_response = cf_client.describe_stacks(StackName=stack_name)
    cf_stacks = cf_response["Stacks"]
    cf_stack = cf_stacks[0]
    stack_status = cf_stack["StackStatus"]
    return stack_status ==  "CREATE_COMPLETE"

def assets(members):
    curr_account = boto3.client('sts').get_caller_identity().get('Account')
    if members:
        def get_accounts():
            for acc in boto3.client('organizations').list_accounts()["Accounts"]:
                yield acc
        accounts = get_accounts()
    else:
        accounts = [{"Id": curr_account}]
    for acc in accounts:
        if acc["Id"] == curr_account:
            session = boto3.session.Session()
        else:
            role_info = {
                'RoleArn': 'arn:aws:iam::%s:role/OrganizationAccountAccessRole' % acc["Id"],
                'RoleSessionName': 'araaliapi'
            }
            credentials = boto3.client('sts').assume_role(**role_info)
            session = boto3.session.Session(
                aws_access_key_id=credentials['Credentials']['AccessKeyId'],
                aws_secret_access_key=credentials['Credentials']['SecretAccessKey'],
                aws_session_token=credentials['Credentials']['SessionToken']
            )

        ec2_client = session.resource("ec2")
        for instance in ec2_client.instances.all():
            # 'ami_launch_index', 'architecture', 'attach_classic_link_vpc',
            # 'attach_volume', 'block_device_mappings', 'boot_mode',
            # 'capacity_reservation_id', 'capacity_reservation_specification',
            # 'classic_address', 'client_token', 'console_output',
            # 'cpu_options', 'create_image', 'create_tags', 'delete_tags',
            # 'describe_attribute', 'detach_classic_link_vpc', 'detach_volume',
            # 'ebs_optimized', 'elastic_gpu_associations',
            # 'elastic_inference_accelerator_associations', 'ena_support',
            # 'enclave_options', 'get_available_subresources',
            # 'hibernation_options', 'hypervisor', 'iam_instance_profile',
            # 'id', 'image', 'image_id', 'instance_id', 'instance_lifecycle',
            # 'instance_type', 'ipv6_address', 'kernel_id', 'key_name',
            # 'key_pair', 'launch_time', 'licenses', 'load',
            # 'maintenance_options', 'meta', 'metadata_options',
            # 'modify_attribute', 'monitor', 'monitoring',
            # 'network_interfaces', 'network_interfaces_attribute',
            # 'outpost_arn', 'password_data', 'placement', 'placement_group',
            # 'platform', 'platform_details', 'private_dns_name',
            # 'private_dns_name_options', 'private_ip_address',
            # 'product_codes', 'public_dns_name', 'public_ip_address',
            # 'ramdisk_id', 'reboot', 'reload', 'report_status',
            # 'reset_attribute', 'reset_kernel', 'reset_ramdisk',
            # 'reset_source_dest_check', 'root_device_name',
            # 'root_device_type', 'security_groups', 'source_dest_check',
            # 'spot_instance_request_id', 'sriov_net_support', 'start',
            # 'state', 'state_reason', 'state_transition_reason', 'stop',
            # 'subnet', 'subnet_id', 'tags', 'terminate', 'tpm_support',
            # 'unmonitor', 'usage_operation', 'usage_operation_update_time',
            # 'virtualization_type', 'volumes', 'vpc', 'vpc_addresses',
            # 'vpc_id', 'wait_until_exists', 'wait_until_running',
            # 'wait_until_stopped', 'wait_until_terminated'
            #print(dir(instance))
            if instance.state["Name"] == "stopped": continue
            yield {
                    "account": acc["Id"],
                    "image_id": instance.image.id,
                    "instance_id": instance.id,
                    "key_name": instance.key_name,
                    "launch-time": instance.launch_time,
                    "state": instance.state["Name"],
                    "subnet": instance.subnet_id,
                    "platform": instance.platform,
                    "public_ip": instance.public_ip_address,
                    "security_groups": instance.security_groups,
                    "tags": instance.tags,
                    "type": instance.instance_type,
                    "vpc": instance.vpc_id,
            }
