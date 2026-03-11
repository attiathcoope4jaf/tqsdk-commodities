#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略18 - 动量策略：棉花期货动量突破策略
原理：
    棉花期货（CF）使用动量指标判断趋势强度。
    动量向上且价格突破近期高点做多，向下且跌破低点做空。

参数：
    - 合约：郑商所CF2505
    - K线周期：30分钟
    - 动量周期：10
    - 周期数：20根K线
    - 止损：2% 
    - 止盈：4%

适用行情：趋势突破行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CZCE.cf2505"          # 棉花期货
KLINE_DURATION = 30 * 60        # 30分钟K线
MOMENTUM_PERIOD = 10            # 动量周期
LOOKBACK_PERIOD = 20            # 周期数
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.04              # 4%止盈

# ============ 主策略 ============
def calculate_momentum(klines, period):
    """计算动量指标"""
    close = klines['close']
    momentum = close.iloc[-1] - close.iloc[-period]
    return momentum

def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：棉花期货动量突破策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=LOOKBACK_PERIOD + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    prev_momentum = None
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < LOOKBACK_PERIOD:
                continue
                
            current_price = klines['close'].iloc[-1]
            
            # 计算动量
            momentum = calculate_momentum(klines, MOMENTUM_PERIOD)
            
            # 计算近期高低点
            recent_high = klines['high'].iloc[-LOOKBACK_PERIOD:].max()
            recent_low = klines['low'].iloc[-LOOKBACK_PERIOD:].min()
            
            print(f"价格: {current_price}, 动量: {momentum:.2f}, 高点: {recent_high:.2f}, 低点: {recent_low:.2f}")
            
            if position == 0:
                # 做多信号：动量向上且突破高点
                if momentum > 0 and current_price > recent_high:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 动量突破: {current_price}")
                # 做空信号：动量向下且跌破低点
                elif momentum < 0 and current_price < recent_low:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 动量跌破: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 动量转负平仓
                elif momentum < 0:
                    print(f"[平仓] 动量转负: {current_price}")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 动量转正平仓
                elif momentum > 0:
                    print(f"[平仓] 动量转正: {current_price}")
                    position = 0
            
            prev_momentum = momentum

if __name__ == "__main__":
    main()
