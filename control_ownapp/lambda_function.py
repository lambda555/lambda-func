import sys
import ec2
import natgw
import alb

def lambda_handler(event, context):
    print("■ 開始")

    # アクション
    action = ""
    
    try:
        # アクションを取得する
        action = event["Action"]

        # アクションが Start/Stop 以外の場合 
        if not(action in ("Start", "Stop")):
            raise Exception('> アクションには \"Start\" または \"Stop\"を指定してください' + '\n' + action)

        # EC2の起動/停止
        ec2.ec2_handler(action)

        # NATゲートウェイの作成/削除
        natgw.natgw_handler(action)

        # ALBの作成/削除
        alb.alb_handler(action)
    
    except KeyError as e:
        print('> キーが指定されていません\n', e)
        sys.exit('> プログラムを終了します')
    except Exception as e:
        print(e)
        sys.exit('> プログラムを終了します')

    print("■ 終了")
