#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 23
策略名称: 螺纹钢多品种截面动量策略
生成日期: 2026-03-17
仓库地址: tqsdk-commodities
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个截面动量策略，同时监控螺纹钢、热卷、铁矿石、焦煤、焦炭五个品种，
根据各品种的动量强度进行排名，做多动量最强的品种，做空动量最弱的品种。

策略逻辑：
1. 计算各品种过去20日的动量（收益率）
2. 按动量大小排序
3. 做多排名Top1的品种，做空排名Bottom1的品种
4. 每日收盘前平仓（不持隔夜仓）

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOLS | 黑色系5品种 | 交易品种列表 |
| MOMENTUM_PERIOD | 20 | 动量计算周期 |
| LOOKBACK_PERIOD | 5 | 持仓周期（交易日） |
| LOT_SIZE | 1 | 单品种开仓手数 |

【风险提示】

- 截面动量策略可能出现回撤
- 品种相关性变化可能导致策略失效
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time

# ============ 参数配置 ============
SYMBOLS = [
    "SHFE.rb2510",   # 螺纹钢
    "SHFE.hc2510",   # 热卷
    "DCE.i2509",     # 铁矿石
    "DCE.jm2509",    # 焦煤
    "DCE.j2509",     # 焦炭
]
KLINE_DURATION = 60 * 60        # 1小时K线
MOMENTUM_PERIOD = 20            # 动量计算周期
LOOKBACK_PERIOD = 5             # 持仓周期（交易日）
LOT_SIZE = 1                    # 单品种开仓手数
CLOSE_TIME = time(14, 55)       # 平仓时间（14:55前）


class CrossSectionalMomentumStrategy:
    def __init__(self, api):
        self.api = api
        self.position = {}  # symbol -> position
        self.last_rebalance_date = None
        
    def calculate_momentum(self, symbol, period=20):
        """计算品种动量（过去N日收益率）"""
        try:
            klines = self.api.get_kline_serial(symbol, 60*60*24, period+1)
            if len(klines) < period + 1:
                return 0
            close_prices = klines['close'].values
            momentum = (close_prices[-1] - close_prices[0]) / close_prices[0]
            return momentum
        except:
            return 0
    
    def get_rankings(self):
        """获取各品种动量排名"""
        momentum_dict = {}
        for symbol in SYMBOLS:
            momentum = self.calculate_momentum(symbol, MOMENTUM_PERIOD)
            momentum_dict[symbol] = momentum
        
        # 按动量排序
        sorted_symbols = sorted(momentum_dict.items(), key=lambda x: x[1], reverse=True)
        return sorted_symbols
    
    def rebalance(self, rankings):
        """重新平衡仓位"""
        if len(rankings) < 2:
            return
        
        # 做多动量最强，做空动量最弱
        long_symbol = rankings[0][0]
        short_symbol = rankings[-1][0]
        
        # 平掉其他仓位
        for symbol in self.position:
            if symbol != long_symbol and symbol != short_symbol:
                if self.position[symbol] != 0:
                    self.close_position(symbol)
        
        # 开多仓
        if self.position.get(long_symbol, 0) != LOT_SIZE:
            self.close_position(long_symbol)
            self.open_position(long_symbol, 1, LOT_SIZE)
        
        # 开空仓
        if self.position.get(short_symbol, 0) != -LOT_SIZE:
            self.close_position(short_symbol)
            self.open_position(short_symbol, -1, LOT_SIZE)
    
    def open_position(self, symbol, direction, volume):
        """开仓"""
        try:
            if direction > 0:
                self.api.insert_order(symbol=symbol, direction="BUY", offset="OPEN", volume=volume)
            else:
                self.api.insert_order(symbol=symbol, direction="SELL", offset="OPEN", volume=volume)
            self.position[symbol] = direction * volume
        except Exception as e:
            print(f"开仓失败 {symbol}: {e}")
    
    def close_position(self, symbol):
        """平仓"""
        try:
            pos = self.position.get(symbol, 0)
            if pos > 0:
                self.api.insert_order(symbol=symbol, direction="SELL", offset="CLOSE", volume=pos)
            elif pos < 0:
                self.api.insert_order(symbol=symbol, direction="BUY", offset="CLOSE", volume=abs(pos))
            self.position[symbol] = 0
        except Exception as e:
            print(f"平仓失败 {symbol}: {e}")
    
    def should_close(self):
        """判断是否应该平仓"""
        current_time = datetime.now().time()
        return current_time >= CLOSE_TIME
    
    def run(self):
        """运行策略"""
        print("=" * 50)
        print("螺纹钢多品种截面动量策略启动")
        print("=" * 50)
        
        while True:
            self.api.wait_update()
            
            # 每日重新平衡
            current_date = datetime.now().date()
            if self.last_rebalance_date != current_date:
                print(f"\n[{datetime.now()}] 执行重新平衡...")
                rankings = self.get_rankings()
                print("动量排名:", [(s, f"{m:.2%}") for s, m in rankings])
                self.rebalance(rankings)
                self.last_rebalance_date = current_date
            
            # 收盘前平仓
            if self.should_close():
                print(f"\n[{datetime.now()}] 收盘前平仓...")
                for symbol in list(self.position.keys()):
                    if self.position.get(symbol, 0) != 0:
                        self.close_position(symbol)
                break


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 模拟测试
    # api = TqApi(auth=TqSim())
    
    try:
        strategy = CrossSectionalMomentumStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
