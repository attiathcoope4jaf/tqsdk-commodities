#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略17 - 均线交叉策略：锌期货双均线交叉策略
原理：
    锌期货（ZN）使用快慢均线交叉判断趋势方向。
    短期均线上穿长期均线时做多，下穿时做空。

参数：
    - 合约：上期所ZN2506
    - K线周期：30分钟
    - 短期均线：10日
    - 长期均线：20日
    - 止损：2% 
    - 止盈：4%

适用行情：趋势行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA
import numpy as np

# ============ 参数配置 ============
SYMBOL = "SHFE.zn2506"          # 锌期货
KLINE_DURATION = 30 * 60        # 30分钟K线
FAST_MA = 10                    # 短期均线
SLOW_MA = 20                    # 长期均线
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.04              # 4%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：锌期货双均线交叉策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=SLOW_MA + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    prev_fast = None
    prev_slow = None
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < SLOW_MA:
                continue
                
            current_price = klines['close'].iloc[-1]
            
            # 计算均线
            fast_ma = MA(klines['close'], FAST_MA).iloc[-1]
            slow_ma = MA(klines['close'], SLOW_MA).iloc[-1]
            
            print(f"价格: {current_price}, 短期均线: {fast_ma:.2f}, 长期均线: {slow_ma:.2f}")
            
            if position == 0 and prev_fast is not None and prev_slow is not None:
                # 做多信号：短期均线上穿长期均线
                if prev_fast <= prev_slow and fast_ma > slow_ma:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 均线金叉: {current_price}")
                # 做空信号：短期均线下穿长期均线
                elif prev_fast >= prev_slow and fast_ma < slow_ma:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 均线死叉: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 均线死叉平仓
                elif fast_ma < slow_ma:
                    print(f"[平仓] 均线死叉: {current_price}")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 均线金叉平仓
                elif fast_ma > slow_ma:
                    print(f"[平仓] 均线金叉: {current_price}")
                    position = 0
            
            prev_fast = fast_ma
            prev_slow = slow_ma

if __name__ == "__main__":
    main()
