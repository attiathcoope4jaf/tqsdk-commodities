#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略05 - 趋势跟踪：铜价三均线策略
原理：
    铜期货（CU）是重要的工业金属，采用三均线系统判断趋势。
    短周期上穿中长周期均线时做多，下穿时做空。

参数：
    - 合约：SHFE.cu2505
    - 均线周期：MA5, MA20, MA60
    - 止损：3% 
    - 止盈：6%

适用行情：趋势明显的单边行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA
import numpy as np

# ============ 参数配置 ============
SYMBOL = "SHFE.cu2505"          # 铜合约
KLINE_DURATION = 60 * 60        # 1小时K线
MA_SHORT = 5                    # 短周期
MA_MID = 20                     # 中周期
MA_LONG = 60                    # 长周期
STOP_LOSS = 0.03                # 3%止损
TAKE_PROFIT = 0.06              # 6%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：铜三均线趋势策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=MA_LONG + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < MA_LONG:
                continue
                
            ma_short = MA(klines, MA_SHORT).iloc[-1]
            ma_mid = MA(klines, MA_MID).iloc[-1]
            ma_long = MA(klines, MA_LONG).iloc[-1]
            
            current_price = klines['close'].iloc[-1]
            
            print(f"价格: {current_price}, MA5: {ma_short:.2f}, MA20: {ma_mid:.2f}, MA60: {ma_long:.2f}")
            
            if position == 0:
                # 做多信号：三均线多头排列且短均线向上
                if ma_short > ma_mid > ma_long:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 价格: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 均线死叉平仓
                elif ma_short < ma_mid:
                    print(f"[平仓] 均线死叉")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
