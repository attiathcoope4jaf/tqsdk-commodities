#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 24
策略名称: 金属板块跨品种对冲策略
生成日期: 2026-03-17
仓库地址: tqsdk-commodities
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个跨品种对冲策略，基于金属板块内部的价格均衡关系进行交易。
使用铜-铝、锌-镍等产业链关联品种进行配对交易。

策略逻辑：
1. 选择具有协整关系的金属品种对（Cu-Al, Zn-Ni）
2. 计算价差的z-score
3. 当价差偏离均值超过2个标准差时入场
4. 当价差回归均值时平仓

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| PAIRS | 配对列表 | 交易品种对 |
| ZSCORE_THRESHOLD | 2.0 | 入场z-score阈值 |
| LOOKBACK_PERIOD | 60 | 计算周期 |
| LOT_SIZE | 1 | 单边开仓手数 |

【风险提示】

- 跨品种对冲策略需关注协整关系变化
- 极端行情可能导致较大偏离
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from collections import deque
from datetime import datetime

# ============ 参数配置 ============
PAIRS = [
    ("SHFE.cu2510", "SHFE.al2510"),  # 铜-铝
    ("SHFE.zn2510", "SHFE.ni2510"),  # 锌-镍
]
KLINE_DURATION = 60 * 60        # 1小时K线
ZSCORE_THRESHOLD = 2.0          # 入场阈值
LOOKBACK_PERIOD = 60            # 计算周期
LOT_SIZE = 1                    # 单边开仓手数


class CrossCommodityHedgeStrategy:
    def __init__(self, api):
        self.api = api
        self.position = {}  # symbol -> position
        self.spread_history = deque(maxlen=LOOKBACK_PERIOD)
        
    def calculate_spread_zscore(self, symbol1, symbol2, period=LOOKBACK_PERIOD):
        """计算价差z-score"""
        try:
            klines1 = self.api.get_kline_serial(symbol1, KLINE_DURATION, period)
            klines2 = self.api.get_kline_serial(symbol2, KLINE_DURATION, period)
            
            if len(klines1) < period or len(klines2) < period:
                return 0, 0
            
            close1 = klines1['close'].values
            close2 = klines2['close'].values
            
            # 计算价差（标准化后）
            spread = close1 / close2
            mean = np.mean(spread)
            std = np.std(spread)
            
            if std == 0:
                return 0, 0
            
            current_spread = spread[-1]
            zscore = (current_spread - mean) / std
            
            return zscore, current_spread
        except Exception as e:
            print(f"计算价差失败: {e}")
            return 0, 0
    
    def check_pair_signals(self, symbol1, symbol2):
        """检查配对交易信号"""
        zscore, spread = self.calculate_spread_zscore(symbol1, symbol2)
        return zscore
    
    def open_pair_position(self, symbol1, symbol2, zscore):
        """开仓"""
        try:
            if zscore > ZSCORE_THRESHOLD:
                # 价差过高，做空symbol1，做多symbol2（预期价差收敛）
                self.api.insert_order(symbol=symbol1, direction="SELL", offset="OPEN", volume=LOT_SIZE)
                self.api.insert_order(symbol=symbol2, direction="BUY", offset="OPEN", volume=LOT_SIZE)
                self.position[symbol1] = -LOT_SIZE
                self.position[symbol2] = LOT_SIZE
                print(f"开仓: 空{symbol1}, 多{symbol2}, zscore={zscore:.2f}")
                
            elif zscore < -ZSCORE_THRESHOLD:
                # 价差过低，做多symbol1，做空symbol2
                self.api.insert_order(symbol=symbol1, direction="BUY", offset="OPEN", volume=LOT_SIZE)
                self.api.insert_order(symbol=symbol2, direction="SELL", offset="OPEN", volume=LOT_SIZE)
                self.position[symbol1] = LOT_SIZE
                self.position[symbol2] = -LOT_SIZE
                print(f"开仓: 多{symbol1}, 空{symbol2}, zscore={zscore:.2f}")
        except Exception as e:
            print(f"开仓失败: {e}")
    
    def close_pair_position(self, symbol1, symbol2):
        """平仓"""
        try:
            pos1 = self.position.get(symbol1, 0)
            pos2 = self.position.get(symbol2, 0)
            
            if pos1 > 0:
                self.api.insert_order(symbol=symbol1, direction="SELL", offset="CLOSE", volume=abs(pos1))
            elif pos1 < 0:
                self.api.insert_order(symbol=symbol1, direction="BUY", offset="CLOSE", volume=abs(pos1))
                
            if pos2 > 0:
                self.api.insert_order(symbol=symbol2, direction="SELL", offset="CLOSE", volume=abs(pos2))
            elif pos2 < 0:
                self.api.insert_order(symbol=symbol2, direction="BUY", offset="CLOSE", volume=abs(pos2))
            
            self.position[symbol1] = 0
            self.position[symbol2] = 0
            print(f"平仓: {symbol1}, {symbol2}")
        except Exception as e:
            print(f"平仓失败: {e}")
    
    def run(self):
        """运行策略"""
        print("=" * 50)
        print("金属板块跨品种对冲策略启动")
        print("=" * 50)
        
        while True:
            self.api.wait_update()
            
            for symbol1, symbol2 in PAIRS:
                zscore = self.check_pair_signals(symbol1, symbol2)
                
                # 检查是否有持仓
                has_position = abs(self.position.get(symbol1, 0)) > 0
                
                if has_position:
                    # 有持仓，检查是否需要平仓
                    if abs(zscore) < 0.5:  # 回归均值
                        self.close_pair_position(symbol1, symbol2)
                else:
                    # 无持仓，检查是否需要开仓
                    if abs(zscore) > ZSCORE_THRESHOLD:
                        self.open_pair_position(symbol1, symbol2, zscore)


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 模拟测试
    # api = TqApi(auth=TqSim())
    
    try:
        strategy = CrossCommodityHedgeStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
