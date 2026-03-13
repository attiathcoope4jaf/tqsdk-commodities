#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略19 - 跨品种对冲策略：螺纹钢与热卷价差交易策略
原理：
    螺纹钢(RB)和热卷(HC)具有高度相关性，利用两者价差的均值回归特性进行套利。
    当价差偏离历史均值时入场，价差回归时平仓获利。

参数：
    - 合约：SHFE.rb2505 + SHFE.hc2505
    - K线周期：日线
    - 布林带周期：20
    - 布林带标准差：2
    - 仓位：各1手
    - 止损：2%

适用行情：价差偏离均值的回归行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import BOLL
import numpy as np

# ============ 参数配置 ============
SYMBOL_LONG = "SHFE.rb2505"     # 螺纹钢（多头）
SYMBOL_SHORT = "SHFE.hc2505"   # 热卷（空头）
KLINE_DURATION = 60 * 60 * 24  # 日K线
BOLL_PERIOD = 20                # 布林带周期
BOLL_STD = 2                   # 标准差倍数
STOP_LOSS = 0.02               # 2%止损

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：螺纹钢-热卷跨品种对冲策略")
    
    klines_rb = api.get_kline_serial(SYMBOL_LONG, KLINE_DURATION, data_length=BOLL_PERIOD + 50)
    klines_hc = api.get_kline_serial(SYMBOL_SHORT, KLINE_DURATION, data_length=BOLL_PERIOD + 50)
    quote_rb = api.get_quote(SYMBOL_LONG)
    quote_hc = api.get_quote(SYMBOL_SHORT)
    
    position = 0  # 0: 空仓, 1: 多RB空HC, -1: 空RB多HC
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines_rb) or api.is_changing(klines_hc):
            if len(klines_rb) < BOLL_PERIOD + 20 or len(klines_hc) < BOLL_PERIOD + 20:
                continue
                
            # 计算价差序列
            spread = klines_rb['close'].values - klines_hc['close'].values
            
            # 计算价差的布林带
            spread_series = pd.Series(spread)
            boll = BOLL(spread_series, period=BOLL_PERIOD, dev=BOLL_STD)
            upper = boll['up'].iloc[-1]
            lower = boll['down'].iloc[-1]
            middle = boll['mid'].iloc[-1]
            
            current_spread = spread[-1]
            
            print(f"当前价差: {current_spread:.2f}, 上轨: {upper:.2f}, 中轨: {middle:.2f}, 下轨: {lower:.2f}")
            
            if position == 0:
                # 做多价差信号：价差低于下轨（RB相对HC低估）
                if current_spread < lower:
                    position = 1
                    print(f"[开多价差] RB做多, HC做空, 价差: {current_spread:.2f}")
                # 做空价差信号：价差高于上轨（RB相对HC高估）
                elif current_spread > upper:
                    position = -1
                    print(f"[开空价差] RB做空, HC做多, 价差: {current_spread:.2f}")
                    
            elif position == 1:
                # 价差回归中轨或高于中轨时平仓
                if current_spread >= middle:
                    position = 0
                    print(f"[平仓] 价差回归, 价差: {current_spread:.2f}")
                # 价差继续扩大超过2%止损
                elif current_spread < lower * 1.02:
                    position = 0
                    print(f"[止损] 价差扩大, 价差: {current_spread:.2f}")
                    
            elif position == -1:
                # 价差回归中轨或低于中轨时平仓
                if current_spread <= middle:
                    position = 0
                    print(f"[平仓] 价差回归, 价差: {current_spread:.2f}")
                # 价差继续扩大超过2%止损
                elif current_spread > upper * 1.02:
                    position = 0
                    print(f"[止损] 价差扩大, 价差: {current_spread:.2f}")
    
    api.close()


if __name__ == "__main__":
    main()
