#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略14 - 突破策略：锌价高低点突破策略
原理：
    锌期货（ZN）使用N日高低点突破判断趋势。
    价格突破N日高点时做多，跌破N日低点时做空。

参数：
    - 合约：SHFE.zn2505
    - 突破周期：20日
    - 止损：3% 
    - 止盈：6%

适用行情：趋势启动的初期
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOL = "SHFE.zn2505"          # 锌合约
KLINE_DURATION = 60 * 60        # 1小时K线
BREAK_PERIOD = 20               # 突破周期
STOP_LOSS = 0.03                # 3%止损
TAKE_PROFIT = 0.06              # 6%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：锌价高低点突破策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=BREAK_PERIOD + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < BREAK_PERIOD:
                continue
                
            high_prices = klines['high'].iloc[-BREAK_PERIOD:]
            low_prices = klines['low'].iloc[-BREAK_PERIOD:]
            
            highest = high_prices.max()
            lowest = low_prices.min()
            
            current_price = klines['close'].iloc[-1]
            
            print(f"价格: {current_price}, {BREAK_PERIOD}日高点: {highest:.2f}, {BREAK_PERIOD}日低点: {lowest:.2f}")
            
            if position == 0:
                # 做多信号：突破20日高点
                if current_price > highest:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 突破20日高点: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 跌破20日低点平仓
                elif current_price < lowest:
                    print(f"[平仓] 跌破20日低点")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
