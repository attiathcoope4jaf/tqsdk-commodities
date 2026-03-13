#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略20 - 多因子策略：橡胶期货多因子量化策略
原理：
    综合使用布林带、RSI、MACD三个因子进行综合判断。
    多个因子同时发出同向信号时入场，提高信号可靠性。

参数：
    - 合约：SHFE.ru2505
    - K线周期：1小时
    - 布林带周期：20，标准差：2
    - RSI周期：14，阈值：30/70
    - MACD参数：12,26,9
    - 止损：3%
    - 止盈：6%

适用行情：多因子共振的单边趋势行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import BOLL, RSI, MACD
import numpy as np

# ============ 参数配置 ============
SYMBOL = "SHFE.ru2505"           # 橡胶期货
KLINE_DURATION = 60 * 60        # 1小时K线

# 布林带参数
BOLL_PERIOD = 20
BOLL_STD = 2

# RSI参数
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# MACD参数
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# 止损止盈
STOP_LOSS = 0.03    # 3%止损
TAKE_PROFIT = 0.06 # 6%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：橡胶期货多因子策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=100)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < max(BOLL_PERIOD, RSI_PERIOD, MACD_SLOW) + 10:
                continue
                
            close_prices = klines['close']
            current_price = close_prices.iloc[-1]
            
            # 计算布林带
            boll = BOLL(close_prices, period=BOLL_PERIOD, dev=BOLL_STD)
            boll_upper = boll['up'].iloc[-1]
            boll_lower = boll['down'].iloc[-1]
            
            # 计算RSI
            rsi = RSI(close_prices, period=RSI_PERIOD)
            rsi_value = rsi.iloc[-1]
            
            # 计算MACD
            macd = MACD(close_prices, fast_period=MACD_FAST, slow_period=MACD_SLOW, signal_period=MACD_SIGNAL)
            macd_diff = macd['diff'].iloc[-1]
            macd_dea = macd['dea'].iloc[-1]
            macd_hist = macd_diff - macd_dea
            macd_hist_prev = macd['diff'].iloc[-2] - macd['dea'].iloc[-2]
            
            # 因子信号
            signal_long = 0
            signal_short = 0
            
            # 布林带信号
            if current_price > boll_upper:
                signal_long += 1
            elif current_price < boll_lower:
                signal_short += 1
                
            # RSI信号
            if rsi_value < RSI_OVERSOLD:
                signal_long += 1
            elif rsi_value > RSI_OVERBOUGHT:
                signal_short += 1
                
            # MACD信号
            if macd_hist > 0 and macd_hist_prev < 0:
                signal_long += 1
            elif macd_hist < 0 and macd_hist_prev > 0:
                signal_short += 1
                
            # 多因子共振（至少2个因子同向）
            print(f"价格: {current_price:.2f}, RSI: {rsi_value:.2f}, MACD: {macd_hist:.4f}, 多因子信号: {signal_long}/{signal_short}")
            
            if position == 0:
                if signal_long >= 2:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 多因子共振做多, 价格: {current_price}")
                elif signal_short >= 2:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 多因子共振做空, 价格: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # MACD死叉平仓
                elif macd_hist < 0 and macd_hist_prev > 0:
                    print(f"[平仓] MACD死叉")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # MACD金叉平仓
                elif macd_hist > 0 and macd_hist_prev < 0:
                    print(f"[平仓] MACD金叉")
                    position = 0
    
    api.close()


if __name__ == "__main__":
    main()
