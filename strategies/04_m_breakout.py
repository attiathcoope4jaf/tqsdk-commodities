#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略04 - 豆粕突破确认策略
原理：
    豆粕（M）是农产品期货的重要品种，受USDA报告、天气等因素影响。
    本策略使用突破确认模式，减少假突破：
    
    1. 记录过去N周期的最高价和最低价（区间）
    2. 当价格突破区间上沿时，等待回调确认
    3. 确认突破有效后入场做多/做空

参数：
    - 区间周期：20根K线
    - 确认周期：3根K线
    - 止损比例：2%

适用行情：区间突破后的趋势行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
import pandas as pd

# ============ 参数配置 ============
SYMBOL = "M2409"               # 豆粕合约
KLINE_DURATION = 30 * 60       # K线周期：30分钟
LOOKBACK = 20                  # 区间周期
CONFIRM_BARS = 3               # 确认周期
LOT_SIZE = 1                   # 开仓手数
STOP_LOSS_PCT = 0.02          # 止损比例 2%

def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print(f"启动：豆粕突破确认策略 | 合约: {SYMBOL}")
    
    # 获取K线数据
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=LOOKBACK + CONFIRM_BARS + 10)
    
    position = 0  # 1: 多头, -1: 空头, 0: 空仓
    entry_price = 0
    range_high = 0
    range_low = 0
    breakout_direction = 0  # 1: 向上, -1: 向下
    
    while True:
        api.wait_update(klines)
        
        if len(klines) < LOOKBACK + CONFIRM_BARS:
            continue
        
        df = pd.DataFrame(klines)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        
        # 计算区间
        recent_klines = df.iloc[-LOOKBACK-CONFIRM_BARS-1:-CONFIRM_BARS-1]
        range_high = recent_klines['high'].max()
        range_low = recent_klines['low'].min()
        
        current_price = df['close'].iloc[-1]
        
        # 确认周期的价格
        confirm_high = df['high'].iloc[-CONFIRM_BARS:].max()
        confirm_low = df['low'].iloc[-CONFIRM_BARS:].min()
        
        if position == 0:
            # 向上突破确认
            if confirm_high > range_high:
                # 价格突破区间上沿，等待回调
                if current_price < range_high and current_price > range_high * 0.995:
                    print(f"做多 | 突破确认 | 价格: {current_price}, 区间: [{range_low:.0f}, {range_high:.0f}]")
                    api.insert_order(symbol=SYMBOL, direction="long", offset="open", volume=LOT_SIZE)
                    position = 1
                    entry_price = current_price
            
            # 向下突破确认
            elif confirm_low < range_low:
                if current_price > range_low and current_price < range_low * 1.005:
                    print(f"做空 | 突破确认 | 价格: {current_price}, 区间: [{range_low:.0f}, {range_high:.0f}]")
                    api.insert_order(symbol=SYMBOL, direction="short", offset="open", volume=LOT_SIZE)
                    position = -1
                    entry_price = current_price
        
        elif position == 1:
            # 多头止损
            if current_price < entry_price * (1 - STOP_LOSS_PCT):
                print(f"多头止损 | 价格: {current_price}, 止损: {entry_price * (1 - STOP_LOSS_PCT):.2f}")
                api.insert_order(symbol=SYMBOL, direction="short", offset="close", volume=LOT_SIZE)
                position = 0
            
            # 多头平仓：价格回到区间内
            elif current_price < range_low:
                print(f"多头平仓 | 回到区间内")
                api.insert_order(symbol=SYMBOL, direction="short", offset="close", volume=LOT_SIZE)
                position = 0
        
        elif position == -1:
            # 空头止损
            if current_price > entry_price * (1 + STOP_LOSS_PCT):
                print(f"空头止损 | 价格: {current_price}, 止损: {entry_price * (1 + STOP_LOSS_PCT):.2f}")
                api.insert_order(symbol=SYMBOL, direction="long", offset="close", volume=LOT_SIZE)
                position = 0
            
            # 空头平仓：价格回到区间内
            elif current_price > range_high:
                print(f"空头平仓 | 回到区间内")
                api.insert_order(symbol=SYMBOL, direction="long", offset="close", volume=LOT_SIZE)
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
