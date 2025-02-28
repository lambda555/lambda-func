import boto3
import os
import sys

# EC2インスタンスのID
instances_ids = [os.environ["BASTION_EC2_INSTANCE_ID"], os.environ["PROD_EC2_INSTANCE_ID"]]
# EC2クライアント
client = boto3.client("ec2", region_name=os.environ["REGION_NAME"])

def ec2_handler(action):
    print("---EC2インスタンス---")
    try:
        # start の場合
        if action == "start":
            # 起動処理
            response = client.start_instances(InstanceIds=instances_ids)
            # EC2インスタンスの起動完了を待つ
            client.get_waiter('instance_running').wait(InstanceIds=instances_ids)
            
            # 起動確認
            for value in response['StartingInstances']:
                print('> インスタンスID: ' + value['InstanceId'] + ' が起動しました')

        # stop の場合
        elif action == "stop":
            # 停止処理
            response = client.stop_instances(InstanceIds=instances_ids)
            # EC2インスタンスの停止完了を待つ
            client.get_waiter('instance_stopped').wait(InstanceIds=instances_ids)

            # 停止確認
            for value in response['StoppingInstances']:
                print('> インスタンスID: ' + value['InstanceId'] + ' が停止しました')
    
    except Exception as e:
        if action == "start":
            print('> 起動処理に失敗しました')
        elif action == "stop":
            print('> 停止処理に失敗しました')
        print(e)
        sys.exit('> プログラムを終了します')
