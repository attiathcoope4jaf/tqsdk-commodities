#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 30
策略名称: 黑色系产业链统计套利与趋势增强策略
生成日期: 2026-03-24
仓库地址: tqsdk-commodities
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略基于黑色系产业链（上中下游）的统计套利关系，在螺纹钢（RB）、
热卷（HC）、铁矿石（I）三个品种之间寻找均值回归和趋势增强的交易机会。

产业链逻辑：
- 铁矿石 → 螺纹钢/热卷（成本传导链）
- 螺纹钢 ↔ 热卷（同类钢材，可替代性强）

策略框架：
【子系统A】螺纹钢-热卷跨品种统计套利
  - 计算 RB/HC 价比的Z-Score
  - Z > 1.5：螺纹钢相对偏贵 → 做空RB/做多HC
  - Z < -1.5：热卷相对偏贵 → 做多RB/做空HC
  - Z 回归到0附近平仓

【子系统B】铁矿石-螺纹钢趋势增强
  - 铁矿石是螺纹钢的成本端，领先螺纹钢约1-3天
  - 当铁矿石出现明确趋势信号时，同向交易螺纹钢
  - 铁矿做多 → RB顺势做多；铁矿做空 → RB顺势做空

【综合判断】
- 当两个子系统信号一致时，仓位加倍（最大2手/品种）
- 信号矛盾时，仅执行套利子系统

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOL_RB | SHFE.rb2509 | 螺纹钢 |
| SYMBOL_HC | SHFE.hc2509 | 热卷 |
| SYMBOL_I | DCE.i2509 | 铁矿石 |
| KLINE_DURATION | 60*60*24 | 日K线 |
| Z_ENTRY | 1.5 | 套利入场Z阈值 |
| Z_EXIT | 0.3 | 套利出场Z阈值 |
| LOOKBACK | 30 | Z-score窗口 |
| MOMENTUM_PERIOD | 5 | 趋势判断短周期 |
| LOT_SIZE | 1 | 开仓手数 |
| CLOSE_TIME | time(14,55) | 收盘前平仓 |

【风险提示】

- 统计套利依赖价差均值回归，结构性变化可能导致失效
- 产业链传导有时滞，跨品种信号可能有延迟
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time

# ============ 参数配置 ============
SYMBOL_RB = "SHFE.rb2509"   # 螺纹钢
SYMBOL_HC = "SHFE.hc2509"   # 热卷
SYMBOL_I = "DCE.i2509"      # 铁矿石
KLINE_DURATION = 60 * 60 * 24   # 日K线
Z_ENTRY = 1.5              # 套利入场Z阈值
Z_EXIT = 0.3                # 套利出场Z阈值
LOOKBACK = 30               # Z-score窗口
MOMENTUM_PERIOD = 5        # 趋势判断短周期
LOT_SIZE = 1               # 开仓手数
CLOSE_TIME = time(14, 55)  # 收盘前平仓


class BlackMetalsStatArbStrategy:
    """黑色系产业链统计套利与趋势增强策略"""

    def __init__(self, api):
        self.api = api
        self.positions = {SYMBOL_RB: 0, SYMBOL_HC: 0, SYMBOL_I: 0}
        self.spread_z = 0
        self.iron_trend = 0   # 铁矿趋势方向

    def calculate_ratio_z(self):
        """计算螺纹钢/热卷 价比的Z-Score"""
        try:
            kl_rb = self.api.get_kline_serial(SYMBOL_RB, KLINE_DURATION, LOOKBACK + 5)
            kl_hc = self.api.get_kline_serial(SYMBOL_HC, KLINE_DURATION, LOOKBACK + 5)
            if len(kl_rb) < LOOKBACK + 1 or len(kl_hc) < LOOKBACK + 1:
                return 0
            rb_closes = kl_rb['close'].values
            hc_closes = kl_hc['close'].values
            # 计算价比序列
            min_len = min(len(rb_closes), len(hc_closes))
            ratio = rb_closes[-min_len:] / hc_closes[-min_len:]
            ratio = ratio[-LOOKBACK - 1:]
            if len(ratio) < LOOKBACK + 1:
                return 0
            mean = np.mean(ratio[:-1])
            std = np.std(ratio[:-1])
            current_ratio = ratio[-1]
            z = (current_ratio - mean) / std if std > 0 else 0
            return z
        except Exception as e:
            print(f"价比Z计算失败: {e}")
            return 0

    def calculate_iron_momentum(self, period=MOMENTUM_PERIOD):
        """计算铁矿石短期动量方向"""
        try:
            kl = self.api.get_kline_serial(SYMBOL_I, KLINE_DURATION, period + 2)
            if len(kl) < period + 1:
                return 0
            prices = kl['close'].values
            mom = (prices[-1] - prices[-period]) / prices[-period]
            return mom
        except Exception as e:
            print(f"铁矿动量计算失败: {e}")
            return 0

    def get_iron_trend_direction(self):
        """判断铁矿趋势方向（趋势增强信号）"""
        mom = self.calculate_iron_momentum()
        if mom > 0.01:
            return 1     # 铁矿上涨趋势 → 做多RB
        elif mom < -0.01:
            return -1    # 铁矿下跌趋势 → 做空RB
        return 0        # 无明确趋势

    # ---- 套利子系统 ----
    def execute_spread_trade(self, z):
        """执行螺纹钢-热卷套利"""
        if z > Z_ENTRY:
            # 螺纹钢偏贵 → 做空RB / 做多HC
            print(f"[套利] Z={z:.2f} > {Z_ENTRY} → 做空螺纹钢/做多热卷")
            self.execute_rb_short_hc_long()
        elif z < -Z_ENTRY:
            # 热卷偏贵 → 做多RB / 做空HC
            print(f"[套利] Z={z:.2f} < {-Z_ENTRY} → 做多螺纹钢/做空热卷")
            self.execute_rb_long_hc_short()
        elif abs(z) <= Z_EXIT:
            # 价差回归 → 平仓
            print(f"[套利] Z={z:.2f} 回归中性 → 平仓")
            self.close_rb_hc()

    def execute_rb_short_hc_long(self):
        """做空螺纹钢/做多热卷"""
        if self.positions[SYMBOL_RB] >= 0:
            self.close_position(SYMBOL_RB)
            self.api.insert_order(symbol=SYMBOL_RB, direction="SELL", offset="OPEN", volume=LOT_SIZE)
            self.positions[SYMBOL_RB] = -1
            print(f"[{datetime.now()}] 做空{SYMBOL_RB}")
        if self.positions[SYMBOL_HC] <= 0:
            self.close_position(SYMBOL_HC)
            self.api.insert_order(symbol=SYMBOL_HC, direction="BUY", offset="OPEN", volume=LOT_SIZE)
            self.positions[SYMBOL_HC] = 1
            print(f"[{datetime.now()}] 做多{SYMBOL_HC}")

    def execute_rb_long_hc_short(self):
        """做多螺纹钢/做空热卷"""
        if self.positions[SYMBOL_RB] <= 0:
            self.close_position(SYMBOL_RB)
            self.api.insert_order(symbol=SYMBOL_RB, direction="BUY", offset="OPEN", volume=LOT_SIZE)
            self.positions[SYMBOL_RB] = 1
            print(f"[{datetime.now()}] 做多{SYMBOL_RB}")
        if self.positions[SYMBOL_HC] >= 0:
            self.close_position(SYMBOL_HC)
            self.api.insert_order(symbol=SYMBOL_HC, direction="SELL", offset="OPEN", volume=LOT_SIZE)
            self.positions[SYMBOL_HC] = -1
            print(f"[{datetime.now()}] 做空{SYMBOL_HC}")

    # ---- 趋势增强子系统 ----
    def execute_trend_enhancement(self, iron_trend):
        """执行铁矿趋势增强（仅螺纹钢）"""
        if iron_trend == 1 and self.positions[SYMBOL_RB] != 1:
            # 铁矿上涨 → 顺势做多RB（加仓）
            self.close_position(SYMBOL_RB)
            self.api.insert_order(symbol=SYMBOL_RB, direction="BUY", offset="OPEN", volume=LOT_SIZE)
            self.positions[SYMBOL_RB] = 1
            print(f"[趋势增强] 铁矿上涨 → 顺势做多{SYMBOL_RB}")
        elif iron_trend == -1 and self.positions[SYMBOL_RB] != -1:
            # 铁矿下跌 → 顺势做空RB
            self.close_position(SYMBOL_RB)
            self.api.insert_order(symbol=SYMBOL_RB, direction="SELL", offset="OPEN", volume=LOT_SIZE)
            self.positions[SYMBOL_RB] = -1
            print(f"[趋势增强] 铁矿下跌 → 顺势做空{SYMBOL_RB}")

    def close_rb_hc(self):
        """平掉RB和HC仓位"""
        self.close_position(SYMBOL_RB)
        self.close_position(SYMBOL_HC)
        self.positions[SYMBOL_RB] = 0
        self.positions[SYMBOL_HC] = 0

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
        for sym in [SYMBOL_RB, SYMBOL_HC, SYMBOL_I]:
            self.close_position(sym)
        self.positions = {SYMBOL_RB: 0, SYMBOL_HC: 0, SYMBOL_I: 0}
        print(f"[{datetime.now()}] 收盘前全部平仓")

    def run(self):
        """运行策略"""
        print("=" * 60)
        print("黑色系产业链统计套利与趋势增强策略启动")
        print("子系统A: 螺纹钢-热卷跨品种统计套利")
        print("子系统B: 铁矿石-螺纹钢趋势增强")
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
                print(f"\n=== [{today}] 日度评估 ===")

                # 子系统A：统计套利
                z = self.calculate_ratio_z()
                self.spread_z = z
                print(f"[套利] RB/HC 价比Z-Score = {z:.3f}")
                self.execute_spread_trade(z)

                # 子系统B：趋势增强
                iron_trend = self.get_iron_trend_direction()
                self.iron_trend = iron_trend
                iron_mom = self.calculate_iron_momentum()
                print(f"[趋势增强] 铁矿5日动量={iron_mom*100:.2f}%, 信号={iron_trend}")
                if iron_trend != 0:
                    self.execute_trend_enhancement(iron_trend)

                print(f"当前持仓: RB={self.positions[SYMBOL_RB]}, HC={self.positions[SYMBOL_HC]}")


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    # 模拟测试
    # api = TqApi(auth=TqSim())

    try:
        strategy = BlackMetalsStatArbStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
