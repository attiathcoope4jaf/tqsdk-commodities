#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略06 - 区间震荡：白糖区间突破策略
原理：
    白糖（SR）在区间内震荡，当价格突破区间上下沿时顺势交易。
    使用布林带确定区间范围。

参数：
    - 合约：SR2505
    - 布林带周期：20
    - 布林带倍数：2.0
    - 止损：2%
    - 止盈：4%

适用行情：区间震荡行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import BOLL
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CZCE.SR2505"          # 白糖合约
KLINE_DURATION = 60 * 60        # 1小时K线
BOLL_PERIOD = 20                # 布林带周期
BOLL_STD = 2.0                  # 布林带倍数
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.04              # 4%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：白糖区间突破策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=BOLL_PERIOD + 10)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < BOLL_PERIOD:
                continue
                
            boll = BOLL(klines, BOLL_PERIOD, BOLL_STD)
            upper = boll['upper'].iloc[-1]
            lower = boll['lower'].iloc[-1]
            
            current_price = klines['close'].iloc[-1]
            
            print(f"价格: {current_price}, 上轨: {upper:.2f}, 下轨: {lower:.2f}")
            
            if position == 0:
                # 突破上轨做多
                if current_price > upper:
                    position = 1
                    entry_price = current_price
                    print(f"[买入突破] 价格: {current_price}")
                # 突破下轨做空
                elif current_price < lower:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出突破] 价格: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}")
                    position = 0
                elif current_price < lower:
                    print(f"[平仓] 回归下轨")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}")
                    position = 0
                elif current_price > upper:
                    print(f"[平仓] 回归上轨")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
