import boto3
import os
import sys

# EC2クライアント
client = boto3.client("ec2", region_name=os.environ["REGION_NAME"])
# パブリックサブネットID（踏み台環境用）
public_subnet = os.environ["PUBLIC_SUBNET_ID_1"]
# プライベートサブネットID（本番環境用）
private_subnet = os.environ["PROD_PRIVATE_SUBNET_ID"]

def start_natgw(subnet):
    # NATゲートウェイを取得する
    filters = [
        {"Name": "subnet-id", "Values": [subnet]},
        {"Name": "state", "Values": ["available"]},
    ]
    response = client.describe_nat_gateways(Filters=filters)

    # NATゲートウェイが存在している場合
    if response["NatGateways"]:
        print('> NATゲートウェイが既に存在します')
        return response["NatGateways"][0]["NatGatewayId"]

    # 存在していない場合
    else:
        # Elastic IP の取得
        response = client.allocate_address(Domain='vpc')
        allocation_id = response['AllocationId']
        print('> Elastic IP: ' + allocation_id + ' が割り当てられました')

        # NATゲートウェイを作成する
        response = client.create_nat_gateway(SubnetId=subnet, AllocationId=allocation_id)
        nat_gateway_id = response['NatGateway']['NatGatewayId']

        # NATゲートウェイの作成完了を待つ
        client.get_waiter('nat_gateway_available').wait(NatGatewayIds=[nat_gateway_id])
        print('> NATゲートウェイID: ' + nat_gateway_id + ' が作成されました')

        return nat_gateway_id

def stop_natgw():
    # 解放するElastic IP
    allocation_ids = []

    # NATゲートウェイを取得する
    response = client.describe_nat_gateways(Filters=[{"Name": "state", "Values": ["available"]}])

    # NATゲートウェイが見つからない場合
    if not response["NatGateways"]:
        print('> 削除可能なNATゲートウェイはありません')

    # NATゲートウェイが見つかった場合
    else:
        for nat_gateway in response["NatGateways"]:
            # # NATゲートウェイを削除する前にElastic IPを取得しておく（Elastic IP解放時に使うため）
            allocation_ids.append(nat_gateway["NatGatewayAddresses"][0]["AllocationId"])
            # NATゲートウェイを削除する
            client.delete_nat_gateway(NatGatewayId=nat_gateway["NatGatewayId"])
            # NATゲートウェイの削除完了を待つ
            client.get_waiter("nat_gateway_deleted").wait(NatGatewayIds=[nat_gateway["NatGatewayId"]])
            print('> NATゲートウェイID: ' + nat_gateway["NatGatewayId"] + ' が削除されました')

    return allocation_ids

def get_rtb_id(subnet):
    # ルートテーブルIDを取得する
    filters = [{"Name": "association.subnet-id", "Values": [subnet]}]
    response = client.describe_route_tables(Filters=filters)
    return response["RouteTables"][0]["Associations"][0]["RouteTableId"]

def get_routes(rtb):
    # ルートを取得する
    response = client.describe_route_tables(RouteTableIds=[rtb])
    return response["RouteTables"][0]["Routes"]

def atatch_natgw(natgw, subnet):
    # ルートテーブルIDを取得する
    rtb = get_rtb_id(subnet)
    # ルートを取得する
    routes = get_routes(rtb)

    # NATゲートウェイIDをターゲットとしているルートが存在していない場合
    if not any(route.get('DestinationCidrBlock') == "0.0.0.0/0" and route.get('NatGatewayId') == natgw for route in routes):
        client.create_route(DestinationCidrBlock="0.0.0.0/0", NatGatewayId=natgw, RouteTableId=rtb)
        print('> ルートテーブルID: ' + rtb + ' にルートが追加されました')
    
    # ルートが存在している場合
    else:
        print('> ルートテーブルID: ' + rtb + ' にルートが既に追加されています')

def detach_natgw(subnet):
    # ルートテーブルIDを取得する
    rtb = get_rtb_id(subnet)
    # ルートを取得する
    routes = get_routes(rtb)

    # 削除対象のルートの場合
    if any(route.get('DestinationCidrBlock') == "0.0.0.0/0" for route in routes):
        # ルートを削除する
        client.delete_route(DestinationCidrBlock="0.0.0.0/0", RouteTableId=rtb)
        print('> ルートテーブルID: ' + rtb + ' からルートが削除されました')

    # そうでない場合
    else:
        print('> ルートテーブルID: ' + rtb + ' に削除対象のルートはありません')

def release_allocation_ids(allocation_ids = []):
    # Elastic IPを取得する
    response = client.describe_addresses()

    for eip in response["Addresses"]:
        # 関連付けがされていない　かつ　削除したNATゲートウェイに関連づいていなかったElastic IPの場合
        if not 'AssociationId' in eip.keys() and not eip['AllocationId'] in allocation_ids:
            # 解放対象のElastic IPに含める
            allocation_ids.append(eip['AllocationId'])

    # 解放対象のElastic IPがある場合
    if allocation_ids:
        for allocation_id in allocation_ids:
            # 解放する
            client.release_address(AllocationId=allocation_id)
            print('> Elastic IP: ' + allocation_id + ' が解放されました')

    # そうでない場合
    else:
        print('> 解放対象のElastic IPはありません')

def natgw_handler(action):
    print("---NAT Gateway---")
    try:
        if action == "Start":
            # NATゲートウェイの作成
            nat_gateway_id = start_natgw(public_subnet)
            # ルーティングの作成
            atatch_natgw(nat_gateway_id, private_subnet)

        elif action == "Stop":
            # ルーティングの削除
            detach_natgw(private_subnet)
            # NATゲートウェイの削除
            allocation_ids = stop_natgw()
            # Elastic IPを解放する
            release_allocation_ids(allocation_ids)

    except Exception as e:
        if action == "Start":
            print('> 作成処理に失敗しました')
        elif action == "Stop":
            print('> 削除処理に失敗しました')
        print(e)
        sys.exit('> プログラムを終了します')
