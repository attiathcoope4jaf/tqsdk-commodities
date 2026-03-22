#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 26
策略名称: 农产品板块多因子轮动策略
生成日期: 2026-03-22
仓库地址: tqsdk-commodities
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个农产品板块多因子轮动策略，同时监控豆粕、玉米、棉花、白糖四个
农产品品种，通过动量、趋势强度、波动率三个因子综合打分，选择最强的品种
做多，同时做空最弱的品种，实现板块内的多空轮动。

策略逻辑：
1. 动量因子（权重40%）：过去20日收益率，动量越强分数越高
2. 趋势因子（权重30%）：价格与20日均线的关系，在均线上方加分
3. 波动率因子（权重30%）：ATR标准化后的波动率，波动率适中最优，过高扣分
4. 综合打分后做多 Top1，做空 Bottom1
5. 每周重新评估并调仓

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOLS | 农产品4品种 | 豆粕/玉米/棉花/白糖 |
| MOMENTUM_PERIOD | 20 | 动量周期（交易日） |
| MA_PERIOD | 20 | 均线周期 |
| ATR_PERIOD | 14 | ATR周期 |
| REBALANCE_WEEKS | 1 | 调仓周期（周） |
| LOT_SIZE | 1 | 单边开仓手数 |
| CLOSE_TIME | time(14,55) | 收盘前平仓时间 |

【风险提示】

- 农产品受季节性和政策影响较大
- 多空轮动需关注品种间相关性变化
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time

# ============ 参数配置 ============
SYMBOLS = [
    "DCE.m2509",     # 豆粕
    "DCE.c2509",     # 玉米
    "CZCE.cf509",    # 棉花
    "CZCE.sr509",    # 白糖
]
KLINE_DURATION = 60 * 60 * 24   # 日K线
MOMENTUM_PERIOD = 20            # 动量周期
MA_PERIOD = 20                  # 均线周期
ATR_PERIOD = 14                 # ATR周期
WEIGHT_MOMENTUM = 0.4           # 动量因子权重
WEIGHT_TREND = 0.3              # 趋势因子权重
WEIGHT_VOL = 0.3                # 波动率因子权重
LOT_SIZE = 1                    # 开仓手数
CLOSE_TIME = time(14, 55)       # 收盘前平仓


class AgriculturalMultiFactorStrategy:
    """农产品板块多因子轮动策略"""

    def __init__(self, api):
        self.api = api
        self.position = {}      # symbol -> position
        self.last_rebalance_week = None

    def calculate_momentum(self, symbol, period=20):
        """计算动量因子（收益率）"""
        try:
            klines = self.api.get_kline_serial(symbol, KLINE_DURATION, period + 2)
            if len(klines) < period + 2:
                return 0
            closes = klines['close'].values
            momentum = (closes[-1] - closes[-period-1]) / closes[-period-1]
            return momentum
        except Exception:
            return 0

    def calculate_trend(self, symbol, period=20):
        """计算趋势因子（价格相对均线偏离度）"""
        try:
            klines = self.api.get_kline_serial(symbol, KLINE_DURATION, period + 2)
            if len(klines) < period + 2:
                return 0
            closes = klines['close'].values
            ma = np.mean(closes[-period:])
            current = closes[-1]
            return (current - ma) / ma
        except Exception:
            return 0

    def calculate_volatility(self, symbol, period=14):
        """计算波动率因子（ATR标准化）"""
        try:
            klines = self.api.get_kline_serial(symbol, KLINE_DURATION, period + 2)
            if len(klines) < period + 2:
                return 0
            highs = klines['high'].values
            lows = klines['low'].values
            closes = klines['close'].values
            trs = np.maximum(
                highs[1:] - lows[1:],
                np.abs(highs[1:] - closes[:-1]),
                np.abs(closes[:-1] - lows[1:])
            )
            atr = np.mean(trs[-period:])
            current_price = closes[-1]
            # 波动率用 ATR/价格 标准化
            return atr / current_price
        except Exception:
            return 0

    def get_factor_scores(self):
        """计算各品种综合打分"""
        results = {}
        for symbol in SYMBOLS:
            momentum = self.calculate_momentum(symbol, MOMENTUM_PERIOD)
            trend = self.calculate_trend(symbol, MA_PERIOD)
            vol = self.calculate_volatility(symbol, ATR_PERIOD)

            # 波动率因子：波动率适中(0.02-0.05)最优，过高或过低扣分
            # 简化处理：波动率越高分数越低（风险调整）
            vol_score = -vol * 10  # 波动率越高越不好

            # 综合得分
            score = (
                WEIGHT_MOMENTUM * momentum * 100 +
                WEIGHT_TREND * trend * 100 +
                WEIGHT_VOL * vol_score
            )

            results[symbol] = {
                "momentum": momentum,
                "trend": trend,
                "volatility": vol,
                "score": score
            }
            print(f"  {symbol}: 动量={momentum:.2%}, 趋势={trend:.2%}, "
                  f"波动率={vol:.4f}, 综合={score:.4f}")
        return results

    def get_rankings(self, scores):
        """按综合得分排名"""
        sorted_symbols = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
        return sorted_symbols

    def rebalance(self, rankings):
        """调仓"""
        if len(rankings) < 2:
            return

        long_symbol = rankings[0][0]
        short_symbol = rankings[-1][0]

        # 平掉所有现有仓位
        for symbol in list(self.position.keys()):
            if symbol not in [long_symbol, short_symbol]:
                self.close_position(symbol)

        # 做多最强
        if self.position.get(long_symbol, 0) != LOT_SIZE:
            self.close_position(long_symbol)
            self.open_position(long_symbol, 1, LOT_SIZE)

        # 做空最弱
        if self.position.get(short_symbol, 0) != -LOT_SIZE:
            self.close_position(short_symbol)
            self.open_position(short_symbol, -1, LOT_SIZE)

        print(f"  -> 做多 {long_symbol}，做空 {short_symbol}")

    def open_position(self, symbol, direction, volume):
        """开仓"""
        try:
            if direction > 0:
                self.api.insert_order(
                    symbol=symbol, direction="BUY", offset="OPEN", volume=volume
                )
            else:
                self.api.insert_order(
                    symbol=symbol, direction="SELL", offset="OPEN", volume=volume
                )
            self.position[symbol] = direction * volume
        except Exception as e:
            print(f"开仓失败 {symbol}: {e}")

    def close_position(self, symbol):
        """平仓"""
        try:
            pos = self.position.get(symbol, 0)
            if pos > 0:
                self.api.insert_order(
                    symbol=symbol, direction="SELL", offset="CLOSE", volume=pos
                )
            elif pos < 0:
                self.api.insert_order(
                    symbol=symbol, direction="BUY", offset="CLOSE", volume=abs(pos)
                )
            self.position[symbol] = 0
        except Exception as e:
            print(f"平仓失败 {symbol}: {e}")

    def should_close(self):
        """判断是否应该收盘前平仓"""
        return datetime.now().time() >= CLOSE_TIME

    def should_rebalance(self):
        """判断是否应该调仓（每周一）"""
        now = datetime.now()
        current_week = now.isocalendar()[1]
        current_weekday = now.weekday()
        if self.last_rebalance_week == current_week:
            return False
        # 每周一调仓
        return current_weekday == 0

    def run(self):
        """运行策略"""
        print("=" * 60)
        print("农产品板块多因子轮动策略启动")
        print(f"监控品种: {', '.join(SYMBOLS)}")
        print("=" * 60)

        while True:
            self.api.wait_update()

            # 收盘前强平
            if self.should_close():
                print(f"\n[{datetime.now()}] 收盘前平仓")
                for symbol in list(self.position.keys()):
                    if self.position.get(symbol, 0) != 0:
                        self.close_position(symbol)
                break

            # 每周调仓
            if self.should_rebalance():
                print(f"\n{'='*40}")
                print(f"[{datetime.now()}] 农产品板块多因子评分（周调仓）")
                print(f"{'='*40}")
                scores = self.get_factor_scores()
                rankings = self.get_rankings(scores)
                print("排名:", [(s, f"{r['score']:.4f}") for s, r in rankings])
                self.rebalance(rankings)
                self.last_rebalance_week = datetime.now().isocalendar()[1]


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    # 模拟测试
    # api = TqApi(auth=TqSim())

    try:
        strategy = AgriculturalMultiFactorStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
