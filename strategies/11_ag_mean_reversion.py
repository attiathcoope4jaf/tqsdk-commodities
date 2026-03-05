#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略11 - 白银均值回归策略
原理：
    白银期货波动性较大，当价格偏离均线过多时，
    价格有回归均值的倾向。

参数：
    - 合约：SHFE.ag2506
    - 周期：15分钟
    - 均线周期：30
    - 偏离阈值：3%

适用行情：震荡行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask
from tqsdk.tafunc import ma

# ============ 参数配置 ============
SYMBOL = "SHFE.ag2506"           # 白银主力合约
KLINE_DURATION = 15 * 60         # 15分钟K线
MA_PERIOD = 30                   # 均线周期
DEVIATION = 0.03                  # 偏离阈值
VOLUME = 1                       # 每次交易手数
DATA_LENGTH = 100                # 历史K线数量


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("账号", "密码"))
    print("启动：白银均值回归策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, DATA_LENGTH)
    target_pos = TargetPosTask(api, SYMBOL)
    
    position = 0  # 0: 空仓, 1: 多, -1: 空
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines.iloc[-1], "datetime"):
            close = klines["close"]
            ma_val = ma(close, MA_PERIOD)
            
            price = close.iloc[-1]
            ma_price = ma_val.iloc[-1]
            deviation = (price - ma_price) / ma_price
            
            print(f"价格: {price:.2f}, 均线: {ma_price:.2f}, 偏离: {deviation*100:.2f}%")
            
            if position == 0:
                # 价格大幅低于均线，做多
                if deviation < -DEVIATION:
                    print(f"[开仓] 做多，价格偏离均线{deviation*100:.2f}%")
                    target_pos.set_target_volume(VOLUME)
                    position = 1
                # 价格大幅高于均线，做空
                elif deviation > DEVIATION:
                    print(f"[开仓] 做空，价格偏离均线{deviation*100:.2f}%")
                    target_pos.set_target_volume(-VOLUME)
                    position = -1
                    
            elif position == 1 and abs(deviation) < DEVIATION / 2:
                print(f"[平仓] 回归均线")
                target_pos.set_target_volume(0)
                position = 0
            elif position == -1 and abs(deviation) < DEVIATION / 2:
                print(f"[平仓] 回归均线")
                target_pos.set_target_volume(0)
                position = 0
    
    api.close()


if __name__ == "__main__":
    main()
