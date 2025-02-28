import boto3
import botocore
import os
import sys

# ELB2クライアント
client = boto3.client("elbv2", region_name=os.environ["REGION_NAME"])

def create_alb():
    try:
        # ALBを取得する
        alb = client.describe_load_balancers(Names=[os.environ["ALB_NAME"]])
        # リスナーを取得する
        listener = client.describe_listeners(LoadBalancerArn=alb["LoadBalancers"][0]["LoadBalancerArn"])

        print('> ロードバランサーが既に存在します')
        print('LoadBalancerArn: ' + alb["LoadBalancers"][0]["LoadBalancerArn"])
        print('TargetGroupArn: ' + listener["Listeners"][0]["DefaultActions"][0]["TargetGroupArn"])
        print('ListenerArn: ' + listener["Listeners"][0]["ListenerArn"])
    
    except botocore.exceptions.ClientError as e:
        # ALBが取得できない場合
        if e.response['Error']['Code'] == 'LoadBalancerNotFound':
            # ALBを作成する
            alb = client.create_load_balancer(
                Name=os.environ["ALB_NAME"],
                Subnets=[os.environ["PUBLIC_SUBNET_ID_1"], os.environ["PUBLIC_SUBNET_ID_2"]],
                SecurityGroups=[os.environ["ALB_SECURITY_GROUP_ID"]],
                Scheme="internet-facing",
                Type="application",
                IpAddressType="ipv4"
            )
            client.get_waiter('load_balancer_available').wait(Names=[os.environ["ALB_NAME"]])

            # ターゲットグループを取得する
            target_group = client.describe_target_groups(Names=[os.environ["TARGET_GROUP_NAME"]])

            # リスナーを作成する
            listener = client.create_listener(
                LoadBalancerArn=alb["LoadBalancers"][0]["LoadBalancerArn"],
                Protocol="HTTP",
                Port=80,
                DefaultActions=[
                    {
                        "Type": "forward",
                        "TargetGroupArn": target_group["TargetGroups"][0]["TargetGroupArn"]
                    }
                ]
            )
            print('> ロードバランサーが作成されました')
            print('LoadBalancerArn: ' + alb["LoadBalancers"][0]["LoadBalancerArn"])
            print('TargetGroupArn: ' + target_group["TargetGroups"][0]["TargetGroupArn"])
            print('ListenerArn: ' + listener["Listeners"][0]["ListenerArn"])
        
        # それ以外の例外の場合
        else:
            raise Exception(e)

def delete_alb():
    try:
        # ALBを取得する
        alb = client.describe_load_balancers(Names=[os.environ["ALB_NAME"]])
        # リスナーを取得する
        listener = client.describe_listeners(LoadBalancerArn=alb["LoadBalancers"][0]["LoadBalancerArn"])

        # リスナーを削除する
        client.delete_listener(ListenerArn=listener["Listeners"][0]["ListenerArn"])
        # ALBを削除する
        client.delete_load_balancer(LoadBalancerArn=alb["LoadBalancers"][0]["LoadBalancerArn"])
        client.get_waiter('load_balancers_deleted').wait(Names=[os.environ["ALB_NAME"]])

        print('> ロードバランサーが削除されました')
        print('LoadBalancerArn: ' + alb["LoadBalancers"][0]["LoadBalancerArn"])
        print('ListenerArn: ' + listener["Listeners"][0]["ListenerArn"])

    except botocore.exceptions.ClientError as e:
        # ALBが取得できない場合
        if e.response['Error']['Code'] == 'LoadBalancerNotFound':
            print('> ロードバランサーは既に存在しません')
    
        # それ以外の例外の場合
        else:
            raise Exception(e)

def alb_handler(action):
    print("---ALB---")
    try:
        if action == "start":
            create_alb()
        elif action == "stop":
            delete_alb()

    except Exception as e:
        if action == "start":
            print('> 作成処理に失敗しました')
        elif action == "stop":
            print('> 削除処理に失敗しました')
        print(e)
        sys.exit('> プログラムを終了します')
