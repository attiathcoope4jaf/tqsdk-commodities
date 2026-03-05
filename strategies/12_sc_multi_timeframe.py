#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略12 - 原油多周期共振策略
原理：
    结合日线和小时线趋势，当两周期趋势一致时入场

参数：
    - 合约：SC2505
    - 大周期：日线
    - 小周期：1小时
    - 均线周期：20

适用行情：趋势行情
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask
from tqsdk.tafunc import ma

# ============ 参数配置 ============
SYMBOL = "SC2505"                # 原油主力合约
KLINE_DURATION_1H = 60 * 60      # 1小时K线
KLINE_DURATION_D = 24 * 60 * 60  # 日线
MA_PERIOD = 20                   # 均线周期
VOLUME = 1                       # 每次交易手数
DATA_LENGTH = 100                # 历史K线数量


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("账号", "密码"))
    print("启动：原油多周期共振策略")
    
    klines_1h = api.get_kline_serial(SYMBOL, KLINE_DURATION_1H, DATA_LENGTH)
    klines_d = api.get_kline_serial(SYMBOL, KLINE_DURATION_D, DATA_LENGTH)
    
    target_pos = TargetPosTask(api, SYMBOL)
    
    position = 0  # 0: 空仓, 1: 多, -1: 空
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines_1h.iloc[-1], "datetime"):
            close_1h = klines_1h["close"]
            close_d = klines_d["close"]
            
            ma_1h = ma(close_1h, MA_PERIOD)
            ma_d = ma(close_d, MA_PERIOD)
            
            price = close_1h.iloc[-1]
            ma_price_1h = ma_1h.iloc[-1]
            ma_price_d = ma_d.iloc[-1]
            
            # 判断两周期趋势
            trend_1h = 1 if price > ma_price_1h else -1
            trend_d = 1 if close_d.iloc[-1] > ma_price_d else -1
            
            print(f"小周期: {price:.2f}/{ma_price_1h:.2f}({trend_1h}), "
                  f"大周期: {close_d.iloc[-1]:.2f}/{ma_price_d:.2f}({trend_d})")
            
            if position == 0:
                # 两周期共振做多
                if trend_1h == 1 and trend_d == 1:
                    print(f"[开仓] 多周期共振做多")
                    target_pos.set_target_volume(VOLUME)
                    position = 1
                # 两周期共振做空
                elif trend_1h == -1 and trend_d == -1:
                    print(f"[开仓] 多周期共振做空")
                    target_pos.set_target_volume(-VOLUME)
                    position = -1
                    
            elif position == 1 and trend_1h == -1:
                print(f"[平仓] 小周期转空")
                target_pos.set_target_volume(0)
                position = 0
            elif position == -1 and trend_1h == 1:
                print(f"[平仓] 小周期转多")
                target_pos.set_target_volume(0)
                position = 0
    
    api.close()


if __name__ == "__main__":
    main()
