#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略09 - 沪铜跨期趋势策略
原理：
    基于沪铜不同到期合约的趋势联动，当近月与远月价差扩大时，
    顺势做多；当价差收窄时，平仓观望。

参数：
    - 近月合约：SHFE.cu2505
    - 远月合约：SHFE.cu2509
    - 周期：1小时
    - 价差均线：20
    - 趋势阈值：50点

适用行情：铜价趋势行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
NEAR_SYMBOL = "SHFE.cu2505"      # 铜近月
FAR_SYMBOL = "SHFE.cu2509"       # 铜远月
KLINE_DURATION = 60 * 60        # 1小时K线
MA_PERIOD = 20                  # 均线周期
TREND_THRESHOLD = 50             # 趋势阈值（元）

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：沪铜跨期趋势策略")
    
    near_quote = api.get_quote(NEAR_SYMBOL)
    far_quote = api.get_quote(FAR_SYMBOL)
    
    near_klines = api.get_kline_serial(NEAR_SYMBOL, KLINE_DURATION, data_length=50)
    far_klines = api.get_kline_serial(FAR_SYMBOL, KLINE_DURATION, data_length=50)
    
    position = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(near_klines) or api.is_changing(far_klines):
            near_price = near_quote.last_price
            far_price = far_quote.last_price
            
            if near_price <= 0 or far_price <= 0:
                continue
            
            # 计算价差
            spread = far_price - near_price
            
            # 计算价差均线
            if len(near_klines) >= MA_PERIOD + 5:
                spread_history = []
                for i in range(MA_PERIOD):
                    f_p = far_klines['close'].iloc[-MA_PERIOD+i]
                    n_p = near_klines['close'].iloc[-MA_PERIOD+i]
                    spread_history.append(f_p - n_p)
                
                spread_ma = np.mean(spread_history)
                trend = spread - spread_ma
                
                print(f"近月: {near_price}, 远月: {far_price}, 价差: {spread}, 均值: {spread_ma:.2f}, 趋势: {trend:.2f}")
                
                # 顺势开仓
                if position == 0:
                    if trend > TREND_THRESHOLD:
                        position = 1
                        print(f"[开仓] 做多价差，价差扩大")
                    elif trend < -TREND_THRESHOLD:
                        position = -1
                        print(f"[开仓] 做空价差，价差收窄")
                
                # 趋势反转平仓
                elif position == 1 and trend < 0:
                    position = 0
                    print(f"[平仓] 趋势反转")
                elif position == -1 and trend > 0:
                    position = 0
                    print(f"[平仓] 趋势反转")
    
    api.close()

if __name__ == "__main__":
    main()
