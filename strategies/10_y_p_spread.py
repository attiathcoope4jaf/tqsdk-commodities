#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略10 - 农产品跨品种套利：豆油棕榈油价差
原理：
    豆油和棕榈油是替代品，存在较强的相关性。
    当两者价差偏离历史均值时，进行价差回归交易。

参数：
    - 豆油合约：DCE.y2505
    - 棕榈油合约：DCE.p2505
    - 周期：1小时
    - 价差窗口：30根K线
    - 开仓阈值：1.5倍标准差
    - 平仓阈值：回归到0.3倍标准差

适用行情：豆油棕榈油价差偏离均值时
作者：attiathcoope4jaf / tqsdk-commodities
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
YO_SYMBOL = "DCE.y2505"         # 豆油
PM_SYMBOL = "DCE.p2505"          # 棕榈油
KLINE_DURATION = 60 * 60        # 1小时K线
WINDOW = 30                     # 价差滚动窗口
OPEN_THRESHOLD = 1.5            # 开仓阈值
CLOSE_THRESHOLD = 0.3           # 平仓阈值

# ============ 价差计算 ============
def calc_spread(y_price, pm_price):
    """计算价差（豆油 - 棕榈油）"""
    return y_price - pm_price

def calc_zscore(spread_series):
    """计算价差的 Z-Score"""
    mean = np.mean(spread_series)
    std = np.std(spread_series)
    if std == 0:
        return 0.0
    return (spread_series[-1] - mean) / std

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：豆油棕榈油跨品种套利策略")
    
    yo_quote = api.get_quote(YO_SYMBOL)
    pm_quote = api.get_quote(PM_SYMBOL)
    
    yo_klines = api.get_kline_serial(YO_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    pm_klines = api.get_kline_serial(PM_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    spread_history = []
    position = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(yo_quote) or api.is_changing(pm_quote):
            yo_price = yo_quote.last_price
            pm_price = pm_quote.last_price
            
            if yo_price <= 0 or pm_price <= 0:
                continue
            
            spread = calc_spread(yo_price, pm_price)
            spread_history.append(spread)
            
            if len(spread_history) < WINDOW:
                continue
            
            recent_spread = spread_history[-WINDOW:]
            zscore = calc_zscore(recent_spread)
            
            print(f"豆油: {yo_price}, 棕榈油: {pm_price}, 价差: {spread:.2f}, Z-Score: {zscore:.2f}")
            
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    print(f"[开仓] 做空价差(卖豆油买棕榈油), Z-Score: {zscore:.2f}")
                    position = -1
                elif zscore < -OPEN_THRESHOLD:
                    print(f"[开仓] 做多价差(买豆油卖棕榈油), Z-Score: {zscore:.2f}")
                    position = 1
                    
            elif position == 1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差回归, Z-Score: {zscore:.2f}")
                position = 0
            elif position == -1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差回归, Z-Score: {zscore:.2f}")
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
