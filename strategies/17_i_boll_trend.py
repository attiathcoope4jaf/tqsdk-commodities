#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略17 - 铁矿石趋势策略：大连商品交易所铁矿石趋势跟踪策略
原理：
    铁矿石期货（I）使用布林带结合趋势过滤来进行趋势交易。
    价格突破布林带上轨且处于上升趋势时做多，下轨且下降趋势时做空。

参数：
    - 合约：大商所I2505
    - K线周期：1小时
    - 布林带周期：20
    - 布林带标准差：2
    - 止损：3% 
    - 止盈：6%

适用行情：趋势明显的单边行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import BOLL
import numpy as np

# ============ 参数配置 ============
SYMBOL = "DCE.I2505"            # 铁矿石期货
KLINE_DURATION = 60 * 60       # 1小时K线
BOLL_PERIOD = 20                # 布林带周期
BOLL_STD = 2                   # 标准差倍数
STOP_LOSS = 0.03               # 3%止损
TAKE_PROFIT = 0.06             # 6%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：铁矿石期货布林带趋势策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=BOLL_PERIOD + 20)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < BOLL_PERIOD + 10:
                continue
                
            current_price = klines['close'].iloc[-1]
            
            # 计算布林带
            boll = BOLL(klines['close'], period=BOLL_PERIOD, dev=BOLL_STD)
            upper = boll['up'].iloc[-1]
            lower = boll['down'].iloc[-1]
            middle = boll['mid'].iloc[-1]
            
            # 计算短期趋势（5周期均线）
            ma5 = klines['close'].rolling(5).mean().iloc[-1]
            ma5_prev = klines['close'].rolling(5).mean().iloc[-2]
            
            print(f"价格: {current_price}, 上轨: {upper:.2f}, 中轨: {middle:.2f}, 下轨: {lower:.2f}")
            
            if position == 0:
                # 做多信号：价格突破上轨且短期均线上升
                if current_price > upper and ma5 > ma5_prev:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 价格突破上轨: {current_price}")
                # 做空信号：价格突破下轨且短期均线下行
                elif current_price < lower and ma5 < ma5_prev:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 价格突破下轨: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 趋势反转平仓
                elif ma5 < ma5_prev:
                    print(f"[平仓] 趋势反转")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 趋势反转平仓
                elif ma5 > ma5_prev:
                    print(f"[平仓] 趋势反转")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
