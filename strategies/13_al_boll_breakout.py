#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略13 - 布林带策略：铝价布林带突破策略
原理：
    铝期货（AL）使用布林带指标判断价格通道。
    价格突破上轨时做多，突破下轨时做空，回归中轨时平仓。

参数：
    - 合约：SHFE.al2505
    - 布林带周期：20周期，2倍标准差
    - 止损：2.5% 
    - 止盈：5%

适用行情：震荡行情中的突破
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import BOLL
import numpy as np

# ============ 参数配置 ============
SYMBOL = "SHFE.al2505"          # 铝合约
KLINE_DURATION = 60 * 60        # 1小时K线
BOLL_PERIOD = 20                # 布林带周期
BOLL_STD = 2                    # 标准差倍数
STOP_LOSS = 0.025               # 2.5%止损
TAKE_PROFIT = 0.05              # 5%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：铝价布林带突破策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=BOLL_PERIOD + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < BOLL_PERIOD:
                continue
                
            boll = BOLL(klines, BOLL_PERIOD, BOLL_STD)
            upper = boll['upper'].iloc[-1]
            middle = boll['mid'].iloc[-1]
            lower = boll['lower'].iloc[-1]
            
            current_price = klines['close'].iloc[-1]
            
            print(f"价格: {current_price}, 上轨: {upper:.2f}, 中轨: {middle:.2f}, 下轨: {lower:.2f}")
            
            if position == 0:
                # 做多信号：价格突破上轨
                if current_price > upper:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 价格突破上轨: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 价格回归中轨平仓
                elif current_price < middle:
                    print(f"[平仓] 价格回归中轨")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
