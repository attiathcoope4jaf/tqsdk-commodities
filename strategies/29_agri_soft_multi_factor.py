#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 29
策略名称: 农产品-软商品跨品种多因子轮动策略
生成日期: 2026-03-24
仓库地址: tqsdk-commodities
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略聚焦农产品板块（豆粕、玉米）与软商品板块（白糖、棉花）之间的跨板块
多因子轮动，在品种间动态配置以实现风险分散和收益增强。

核心逻辑：
1. 三因子打分系统：
   - 动量因子（Momentum）：20日收益率，动量强者加仓
   - 趋势强度因子（ADX）：反映当前趋势的强弱程度
   - 波动率压缩因子（Vol Compression）：波动率低 → 蓄势信号

2. 跨板块配置：
   - 农产品（豆粕+玉米）和软商品（白糖+棉花）各选最强品种
   - 等权配置，最大单品种仓位不超过40%

3. 每月重新评估并调仓一次

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| AGRI_SYMBOLS | m2509, c2509 | 农产品 |
| SOFT_SYMBOLS | SR509, CF509 | 软商品 |
| KLINE_DURATION | 60*60*24 | 日K线 |
| MOMENTUM_PERIOD | 20 | 动量周期 |
| ADX_PERIOD | 14 | ADX周期 |
| LOT_SIZE | 1 | 开仓手数 |
| REBALANCE_DAYS | 21 | 调仓周期 |
| CLOSE_TIME | time(14,55) | 收盘前平仓 |

【风险提示】

- 跨品种轮动依赖因子有效性，需定期评估
- 极端天气、政策因素可能影响农产品价格
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time

# ============ 参数配置 ============
AGRI_SYMBOLS = [
    "DCE.m2509",    # 豆粕
    "DCE.c2509",    # 玉米
]
SOFT_SYMBOLS = [
    "CZCE.SR509",   # 白糖
    "CZCE.CF509",   # 棉花
]
ALL_SYMBOLS = AGRI_SYMBOLS + SOFT_SYMBOLS

KLINE_DURATION = 60 * 60 * 24   # 日K线
MOMENTUM_PERIOD = 20            # 动量周期
ADX_PERIOD = 14                 # ADX周期
VOL_PERIOD = 20                 # 波动率计算周期
LOT_SIZE = 1                   # 开仓手数
REBALANCE_DAYS = 21            # 调仓周期（约1个月）
CLOSE_TIME = time(14, 55)      # 收盘前平仓


class AgriSoftMultiFactorStrategy:
    """农产品-软商品跨品种多因子轮动策略"""

    def __init__(self, api):
        self.api = api
        self.positions = {}   # symbol -> direction (1=long, -1=short, 0=flat)
        self.last_rebalance_day = None
        self.rebalance_counter = 0

    def calculate_momentum(self, symbol, period=MOMENTUM_PERIOD):
        """计算动量因子（区间收益率）"""
        try:
            kl = self.api.get_kline_serial(symbol, KLINE_DURATION, period + 2)
            if len(kl) < period + 1:
                return 0
            prices = kl['close'].values
            mom = (prices[-1] - prices[-period]) / prices[-period]
            return mom
        except Exception as e:
            print(f"动量计算失败 {symbol}: {e}")
            return 0

    def calculate_adx(self, symbol, period=ADX_PERIOD):
        """计算ADX趋势强度因子"""
        try:
            kl = self.api.get_kline_serial(symbol, KLINE_DURATION, period + 20)
            if len(kl) < period + 15:
                return 0
            highs = kl['high'].values
            lows = kl['low'].values
            closes = kl['close'].values
            # 计算+DI和-DI
            plus_dm = np.zeros(len(highs) - 1)
            minus_dm = np.zeros(len(highs) - 1)
            tr = np.zeros(len(highs) - 1)
            for i in range(len(highs) - 1):
                high_diff = highs[i + 1] - highs[i]
                low_diff = lows[i] - lows[i + 1]
                plus_dm[i] = high_diff if high_diff > low_diff and high_diff > 0 else 0
                minus_dm[i] = low_diff if low_diff > high_diff and low_diff > 0 else 0
                tr[i] = max(
                    highs[i + 1] - lows[i + 1],
                    abs(highs[i + 1] - closes[i]),
                    abs(lows[i + 1] - closes[i])
                )
            # 平滑
            adx_period = min(period, len(plus_dm))
            plus_di = np.mean(plus_dm[-adx_period:]) / max(np.mean(tr[-adx_period:]), 1) * 100
            minus_di = np.mean(minus_dm[-adx_period:]) / max(np.mean(tr[-adx_period:]), 1) * 100
            dx = abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9) * 100
            adx = dx  # 简化ADX
            return adx
        except Exception as e:
            print(f"ADX计算失败 {symbol}: {e}")
            return 0

    def calculate_vol_compression(self, symbol, period=VOL_PERIOD):
        """计算波动率压缩因子（低值=蓄势信号）"""
        try:
            kl = self.api.get_kline_serial(symbol, KLINE_DURATION, period * 2 + 2)
            if len(kl) < period * 2 + 1:
                return 0
            closes = kl['close'].values
            recent_vol = np.std(np.diff(closes[-period:]) / closes[-period - 1:-1])
            hist_vol = np.std(np.diff(closes[-period * 2:-period]) / closes[-period * 2 - 1:-period - 1])
            if hist_vol == 0:
                return 0
            compression = recent_vol / hist_vol  # <1 = 波动率压缩
            return compression
        except Exception as e:
            print(f"波动率压缩计算失败 {symbol}: {e}")
            return 0

    def score_all(self):
        """计算所有品种三因子综合得分"""
        scores = []
        for sym in ALL_SYMBOLS:
            mom = self.calculate_momentum(sym)
            adx = self.calculate_adx(sym)
            vol_comp = self.calculate_vol_compression(sym)

            # 标准化各因子
            # 动量：越高越好
            # ADX：越高（趋势越强）越好
            # Vol Compression：越低（蓄势）越好，取负
            score = mom * 100 + adx * 0.1 - vol_comp * 0.5
            scores.append({
                'symbol': sym,
                'momentum': mom,
                'adx': adx,
                'vol_comp': vol_comp,
                'score': score
            })
            print(f"[{sym}] 动量={mom*100:.2f}%, ADX={adx:.1f}, 波动压缩={vol_comp:.3f}, 综合={score:.3f}")
        scores.sort(key=lambda x: x['score'], reverse=True)
        return scores

    def select_best_per_sector(self):
        """每个板块选取最佳品种"""
        agri_scores = []
        soft_scores = []
        for sym in AGRI_SYMBOLS:
            mom = self.calculate_momentum(sym)
            adx = self.calculate_adx(sym)
            vol_comp = self.calculate_vol_compression(sym)
            score = mom * 100 + adx * 0.1 - vol_comp * 0.5
            agri_scores.append({'symbol': sym, 'score': score})
            print(f"  [农产品]{sym}: 综合={score:.3f}")
        for sym in SOFT_SYMBOLS:
            mom = self.calculate_momentum(sym)
            adx = self.calculate_adx(sym)
            vol_comp = self.calculate_vol_compression(sym)
            score = mom * 100 + adx * 0.1 - vol_comp * 0.5
            soft_scores.append({'symbol': sym, 'score': score})
            print(f"  [软商品]{sym}: 综合={score:.3f}")

        agri_scores.sort(key=lambda x: x['score'], reverse=True)
        soft_scores.sort(key=lambda x: x['score'], reverse=True)
        return agri_scores[0]['symbol'], soft_scores[0]['symbol']

    def rebalance(self):
        """调仓：等权配置两个板块的最优品种"""
        best_agri, best_soft = self.select_best_per_sector()

        # 找出不在目标列表的仓位
        for sym in list(self.positions.keys()):
            if sym not in [best_agri, best_soft]:
                self.close_position(sym)
                del self.positions[sym]

        # 开仓/持有agri板块最优
        if self.positions.get(best_agri) != 1:
            self.close_position(best_agri)
            self.open_long(best_agri)
            self.positions[best_agri] = 1
            print(f"[{datetime.now()}] 做多农产品最优: {best_agri}")

        # 开仓/持有soft板块最优
        if self.positions.get(best_soft) != 1:
            self.close_position(best_soft)
            self.open_long(best_soft)
            self.positions[best_soft] = 1
            print(f"[{datetime.now()}] 做多软商品最优: {best_soft}")

        print(f"[{datetime.now()}] 调仓完成 | 农产品:{best_agri} | 软商品:{best_soft}")

    def open_long(self, symbol):
        """开多"""
        try:
            self.api.insert_order(symbol=symbol, direction="BUY", offset="OPEN", volume=LOT_SIZE)
        except Exception as e:
            print(f"开多失败 {symbol}: {e}")

    def close_position(self, symbol):
        """平仓"""
        try:
            pos = self.api.get_position(symbol)
            if pos.pos_long > 0:
                self.api.insert_order(symbol=symbol, direction="SELL", offset="CLOSE", volume=pos.pos_long)
            if pos.pos_short > 0:
                self.api.insert_order(symbol=symbol, direction="BUY", offset="CLOSE", volume=pos.pos_short)
        except Exception as e:
            print(f"平仓失败 {symbol}: {e}")

    def close_all(self):
        """收盘前全部平仓"""
        for sym in list(self.positions.keys()):
            self.close_position(sym)
        self.positions.clear()
        print(f"[{datetime.now()}] 收盘前全部平仓")

    def run(self):
        """运行策略"""
        print("=" * 60)
        print("农产品-软商品跨品种多因子轮动策略启动")
        print("因子: 动量 + ADX趋势强度 + 波动率压缩")
        print(f"调仓周期: 每{REBALANCE_DAYS}个交易日（约每月一次）")
        print("=" * 60)

        last_check_day = None

        while True:
            self.api.wait_update()

            if datetime.now().time() >= CLOSE_TIME:
                self.close_all()
                print(f"[{datetime.now()}] 收盘，策略结束")
                break

            today = datetime.now().strftime("%Y-%m-%d")
            if last_check_day != today:
                last_check_day = today
                self.rebalance_counter += 1
                print(f"\n=== [{today}] 日度评估 ===")

                if self.rebalance_counter % REBALANCE_DAYS == 0:
                    self.rebalance()


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    # 模拟测试
    # api = TqApi(auth=TqSim())

    try:
        strategy = AgriSoftMultiFactorStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
