#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略03 - 原油趋势追踪策略
原理：
    原油（SC）是国内期货市场的重要品种，受地缘政治、供需关系影响大。
    本策略结合趋势指标与波动率过滤，进行趋势追踪。
    
    1. 使用 EMA 确认趋势方向
    2. 使用 ATR 过滤假突破
    3. 趋势回踩确认后入场

参数：
    - 快速EMA周期：12
    - 慢速EMA周期：26
    - ATR周期：14
    - ATR倍数：1.5

适用行情：趋势明显的单边行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import EMA, ATR
import pandas as pd

# ============ 参数配置 ============
SYMBOL = "SC2406"              # 原油合约
KLINE_DURATION = 15 * 60       # K线周期：15分钟
FAST_EMA = 12                  # 快速EMA周期
SLOW_EMA = 26                  # 慢速EMA周期
ATR_PERIOD = 14                # ATR周期
ATR_MULTI = 1.5                # ATR倍数
LOT_SIZE = 1                   # 开仓手数
STOP_LOSS_ATR = 2.0            # 止损：2倍ATR

def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print(f"启动：原油趋势追踪策略 | 合约: {SYMBOL}")
    
    # 获取K线数据
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=100)
    
    position = 0  # 1: 多头, -1: 空头, 0: 空仓
    entry_price = 0
    stop_loss = 0
    
    while True:
        api.wait_update(klines)
        
        if len(klines) < SLOW_EMA + 5:
            continue
        
        # 转换为DataFrame计算指标
        df = pd.DataFrame(klines)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        
        # 计算EMA和ATR
        df['ema_fast'] = EMA(df['close'], FAST_EMA)
        df['ema_slow'] = EMA(df['close'], SLOW_EMA)
        df['atr'] = ATR(df['high'], df['low'], df['close'], ATR_PERIOD)
        
        current_price = df['close'].iloc[-1]
        ema_fast = df['ema_fast'].iloc[-1]
        ema_slow = df['ema_slow'].iloc[-1]
        atr = df['atr'].iloc[-1]
        
        # 交易信号
        if position == 0:
            # 多头信号：快线突破慢线，且价格回踩EMA
            if ema_fast > ema_slow and current_price > ema_fast - atr * ATR_MULTI:
                print(f"做多 | 价格: {current_price}, EMA12: {ema_fast:.2f}, EMA26: {ema_slow:.2f}")
                api.insert_order(symbol=SYMBOL, direction="long", offset="open", volume=LOT_SIZE)
                position = 1
                entry_price = current_price
                stop_loss = entry_price - atr * STOP_LOSS_ATR
            
            # 空头信号：快线跌破慢线
            elif ema_fast < ema_slow and current_price < ema_fast + atr * ATR_MULTI:
                print(f"做空 | 价格: {current_price}, EMA12: {ema_fast:.2f}, EMA26: {ema_slow:.2f}")
                api.insert_order(symbol=SYMBOL, direction="short", offset="open", volume=LOT_SIZE)
                position = -1
                entry_price = current_price
                stop_loss = entry_price + atr * STOP_LOSS_ATR
        
        elif position == 1:
            # 多头止损
            if current_price < stop_loss:
                print(f"多头止损 | 价格: {current_price}, 止损: {stop_loss:.2f}")
                api.insert_order(symbol=SYMBOL, direction="short", offset="close", volume=LOT_SIZE)
                position = 0
            
            # 多头平仓：趋势反转
            elif ema_fast < ema_slow:
                print(f"多头平仓 | 趋势反转")
                api.insert_order(symbol=SYMBOL, direction="short", offset="close", volume=LOT_SIZE)
                position = 0
        
        elif position == -1:
            # 空头止损
            if current_price > stop_loss:
                print(f"空头止损 | 价格: {current_price}, 止损: {stop_loss:.2f}")
                api.insert_order(symbol=SYMBOL, direction="long", offset="close", volume=LOT_SIZE)
                position = 0
            
            # 空头平仓：趋势反转
            elif ema_fast > ema_slow:
                print(f"空头平仓 | 趋势反转")
                api.insert_order(symbol=SYMBOL, direction="long", offset="close", volume=LOT_SIZE)
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
