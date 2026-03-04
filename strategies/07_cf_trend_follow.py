#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略07 - 趋势策略：棉花趋势跟踪策略
原理：
    棉花（CF）具有明显的季节性和趋势特征。
    使用双均线交叉配合ATR止损进行趋势跟踪。

参数：
    - 合约：CZCE.CF2505
    - 周期：1小时
    - 短期均线：10
    - 长期均线：30
    - 止损：3%

适用行情：趋势明显的行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA, ATR
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CZCE.CF2505"          # 棉花合约
KLINE_DURATION = 60 * 60        # 1小时K线
MA_SHORT = 10                    # 短期均线
MA_LONG = 30                     # 长期均线
ATR_PERIOD = 14                  # ATR周期
ATR_STOP = 2.0                   # ATR止损倍数

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：棉花趋势跟踪策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=50)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < MA_LONG:
                continue
                
            ma_short = MA(klines, MA_SHORT).iloc[-1]
            ma_long = MA(klines, MA_LONG).iloc[-1]
            atr = ATR(klines, ATR_PERIOD).iloc[-1]
            
            current_price = klines['close'].iloc[-1]
            
            print(f"价格: {current_price}, MA10: {ma_short:.2f}, MA30: {ma_long:.2f}")
            
            if position == 0:
                # 金叉做多
                if ma_short > ma_long:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 金叉, 价格: {current_price}")
                    
            elif position == 1:
                # 死叉平仓
                if ma_short < ma_long:
                    print(f"[平仓] 死叉, 价格: {current_price}")
                    position = 0
                # ATR止损
                elif current_price < entry_price - atr * ATR_STOP:
                    print(f"[止损] 价格: {current_price}")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
