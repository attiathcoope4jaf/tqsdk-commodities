#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略15 - 布林带策略：白糖期货布林带突破策略
原理：
    白糖期货（SR）使用布林带判断震荡与突破。
    价格突破布林带上轨时做多，跌破下轨时做空，回到中轨平仓。

参数：
    - 合约：郑商所SR2505
    - K线周期：30分钟
    - 布林带周期：20日
    - 布林带宽度：2倍标准差
    - 止损：2% 
    - 止盈：4%

适用行情：震荡突破行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA, STD
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CZCE.SR2505"          # 白糖期货
KLINE_DURATION = 30 * 60        # 30分钟K线
BB_PERIOD = 20                  # 布林带周期
BB_STD = 2                      # 布林带宽度（倍）
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.04              # 4%止盈

# ============ 主策略 ============
def calculate_bollinger_bands(klines, period, std_dev):
    """计算布林带"""
    ma = MA(klines['close'], period)
    std = STD(klines['close'], period)
    upper = ma + std * std_dev
    lower = ma - std * std_dev
    return ma, upper, lower

def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：白糖期货布林带突破策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=BB_PERIOD + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < BB_PERIOD:
                continue
                
            current_price = klines['close'].iloc[-1]
            
            ma, upper, lower = calculate_bollinger_bands(klines, BB_PERIOD, BB_STD)
            ma_val = ma.iloc[-1]
            upper_val = upper.iloc[-1]
            lower_val = lower.iloc[-1]
            
            print(f"价格: {current_price}, 上轨: {upper_val:.2f}, 中轨: {ma_val:.2f}, 下轨: {lower_val:.2f}")
            
            if position == 0:
                # 做多信号：突破布林带上轨
                if current_price > upper_val:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 突破布林带上轨: {current_price}")
                # 做空信号：跌破布林带下轨
                elif current_price < lower_val:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 跌破布林带下轨: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 价格回到中轨平仓
                elif current_price < ma_val:
                    print(f"[平仓] 价格回到中轨")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 价格回到中轨平仓
                elif current_price > ma_val:
                    print(f"[平仓] 价格回到中轨")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
