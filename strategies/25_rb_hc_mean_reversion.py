#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 25
策略名称: 螺纹钢-热卷价差均值回归策略
生成日期: 2026-03-22
仓库地址: tqsdk-commodities
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个价差均值回归策略，基于螺纹钢(SHFE.rb)和热卷(SHFE.hc)的价差
具有均值回归特性进行交易。螺纹钢和热卷同属黑色系钢材，两者价格高度相关，
但短期供需差异会导致价差偏离均值，产生交易机会。

策略逻辑：
1. 计算螺纹钢与热卷的价差（spread = rb - hc）
2. 计算价差的 z-score（标准化偏离度）
3. 当 z-score > 阈值（如1.5）：价差偏高，预期回归 → 做空rb，做多hc
4. 当 z-score < -阈值（如-1.5）：价差偏低 → 做多rb，做空hc
5. 当 z-score 回归至 0 附近：平仓

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOL_LONG | SHFE.rb2510 | 多头品种（螺纹钢） |
| SYMBOL_SHORT | SHFE.hc2510 | 空头品种（热卷） |
| Z_ENTER | 1.5 | 入场阈值（z-score） |
| Z_EXIT | 0.3 | 出场阈值（z-score） |
| LOOKBACK | 30 | 计算 z-score 的历史窗口 |
| LOT_SIZE | 1 | 每边开仓手数 |
| STOP_LOSS | 2.5 | 止损阈值（z-score） |

【风险提示】

- 价差策略需关注品种相关性变化
- 极端行情可能导致价差不回归
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time

# ============ 参数配置 ============
SYMBOL_LONG = "SHFE.rb2510"     # 螺纹钢（多头）
SYMBOL_SHORT = "SHFE.hc2510"    # 热卷（空头）
KLINE_DURATION = 60 * 30        # 30分钟K线
Z_ENTER = 1.5                   # 入场阈值
Z_EXIT = 0.3                   # 出场阈值
LOOKBACK = 30                  # z-score 回看窗口
LOT_SIZE = 1                    # 开仓手数
STOP_LOSS = 2.5                 # 止损阈值
CLOSE_TIME = time(14, 55)       # 收盘前平仓


class SpreadMeanReversionStrategy:
    """螺纹钢-热卷价差均值回归策略"""

    def __init__(self, api):
        self.api = api
        self.position_rb = 0    # 螺纹钢持仓
        self.position_hc = 0   # 热卷持仓
        self.spread_history = []
        self.z_score = 0
        self.entry_z = 0        # 入场时的 z-score

    def get_spread(self):
        """获取当前价差"""
        try:
            rb_kl = self.api.get_kline_serial(SYMBOL_LONG, KLINE_DURATION, 2)
            hc_kl = self.api.get_kline_serial(SYMBOL_SHORT, KLINE_DURATION, 2)
            if len(rb_kl) < 2 or len(hc_kl) < 2:
                return None
            rb_price = rb_kl['close'].values[-1]
            hc_price = hc_kl['close'].values[-1]
            return rb_price - hc_price
        except Exception as e:
            print(f"获取价差失败: {e}")
            return None

    def get_historical_spread(self, n=30):
        """获取历史价差序列"""
        try:
            rb_kl = self.api.get_kline_serial(SYMBOL_LONG, KLINE_DURATION, n + 2)
            hc_kl = self.api.get_kline_serial(SYMBOL_SHORT, KLINE_DURATION, n + 2)
            if len(rb_kl) < n + 2 or len(hc_kl) < n + 2:
                return []
            rb_prices = rb_kl['close'].values
            hc_prices = hc_kl['close'].values
            spreads = rb_prices - hc_prices
            return spreads
        except Exception as e:
            print(f"获取历史价差失败: {e}")
            return []

    def calculate_z_score(self, spreads):
        """计算当前 z-score"""
        if len(spreads) < LOOKBACK:
            return 0
        recent = spreads[-LOOKBACK:]
        mean = np.mean(recent)
        std = np.std(recent)
        if std == 0:
            return 0
        current_spread = spreads[-1]
        z = (current_spread - mean) / std
        return z

    def open_spread_position(self, direction):
        """
        开设价差仓位
        direction > 0: 预期价差上升（多rb，空hc）
        direction < 0: 预期价差下降（空rb，多hc）
        """
        try:
            if direction > 0:
                # 预期价差扩大：多rb，空hc
                self.api.insert_order(
                    symbol=SYMBOL_LONG, direction="BUY", offset="OPEN", volume=LOT_SIZE
                )
                self.api.insert_order(
                    symbol=SYMBOL_SHORT, direction="SELL", offset="OPEN", volume=LOT_SIZE
                )
                self.position_rb = LOT_SIZE
                self.position_hc = -LOT_SIZE
                print(f"[{datetime.now()}] 开多rb空hc，价差方向=扩大")
            else:
                # 预期价差收窄：空rb，多hc
                self.api.insert_order(
                    symbol=SYMBOL_LONG, direction="SELL", offset="OPEN", volume=LOT_SIZE
                )
                self.api.insert_order(
                    symbol=SYMBOL_SHORT, direction="BUY", offset="OPEN", volume=LOT_SIZE
                )
                self.position_rb = -LOT_SIZE
                self.position_hc = LOT_SIZE
                print(f"[{datetime.now()}] 开空rb多hc，价差方向=收窄")
            self.entry_z = self.z_score
        except Exception as e:
            print(f"开仓失败: {e}")

    def close_spread_position(self):
        """平掉价差仓位"""
        try:
            if self.position_rb > 0:
                self.api.insert_order(
                    symbol=SYMBOL_LONG, direction="SELL", offset="CLOSE", volume=self.position_rb
                )
            elif self.position_rb < 0:
                self.api.insert_order(
                    symbol=SYMBOL_LONG, direction="BUY", offset="CLOSE", volume=abs(self.position_rb)
                )
            if self.position_hc > 0:
                self.api.insert_order(
                    symbol=SYMBOL_SHORT, direction="SELL", offset="CLOSE", volume=self.position_hc
                )
            elif self.position_hc < 0:
                self.api.insert_order(
                    symbol=SYMBOL_SHORT, direction="BUY", offset="CLOSE", volume=abs(self.position_hc)
                )
            print(f"[{datetime.now()}] 平仓完成，盈亏z: {abs(self.z_score - self.entry_z):.2f}")
            self.position_rb = 0
            self.position_hc = 0
        except Exception as e:
            print(f"平仓失败: {e}")

    def should_close_all(self):
        """判断是否应该全部平仓（收盘前）"""
        return datetime.now().time() >= CLOSE_TIME

    def run(self):
        """运行策略"""
        print("=" * 60)
        print("螺纹钢-热卷价差均值回归策略启动")
        print(f"入场阈值: Z>{Z_ENTER} 或 Z<-{Z_ENTER}，出场阈值: Z~{Z_EXIT}")
        print("=" * 60)

        while True:
            self.api.wait_update()

            spreads = self.get_historical_spread(LOOKBACK + 5)
            if len(spreads) < LOOKBACK:
                continue

            self.z_score = self.calculate_z_score(spreads)
            current_spread = spreads[-1]

            print(f"[{datetime.now()}] 价差={current_spread:.2f}, z-score={self.z_score:.3f}, "
                  f"rb持仓={self.position_rb}, hc持仓={self.position_hc}")

            # 入场逻辑
            has_position = (self.position_rb != 0) or (self.position_hc != 0)
            if not has_position:
                if self.z_score > Z_ENTER:
                    # 价差偏高，做空价差
                    self.open_spread_position(-1)
                elif self.z_score < -Z_ENTER:
                    # 价差偏低，做多价差
                    self.open_spread_position(1)
            else:
                # 持仓中：检查出场或止损
                pnl_z = abs(self.z_score - self.entry_z)
                if pnl_z >= STOP_LOSS:
                    print(f"[{datetime.now()}] 触发止损，z变化={pnl_z:.3f}")
                    self.close_spread_position()
                elif abs(self.z_score) <= Z_EXIT:
                    print(f"[{datetime.now()}] 价差回归，平仓")
                    self.close_spread_position()

            # 收盘前强平
            if self.should_close_all() and has_position:
                print(f"\n[{datetime.now()}] 收盘前平仓")
                self.close_spread_position()
                break


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    # 模拟测试
    # api = TqApi(auth=TqSim())

    try:
        strategy = SpreadMeanReversionStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
