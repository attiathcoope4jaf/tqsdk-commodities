#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 28
策略名称: 能源-农产品跨市场对冲与品种轮动策略
生成日期: 2026-03-23
仓库地址: tqsdk-commodities
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略利用能源板块（原油、燃料油）与农产品板块（豆油、棕榈油）之间的
产业链联动关系和相对价格变动进行跨市场对冲和品种轮动。

核心逻辑：
1. 原油与豆油/棕榈油存在"替代品"逻辑（生物燃料关联）
2. 当原油上涨，豆油/棕榈油通常跟涨（成本推动）；反之亦然
3. 通过计算能源-农产品相对强弱指标（能源因子/农产品因子），
   在相对强弱极端时入场对冲

策略包含两个子系统：
【子系统A】原油-豆油跨市场对冲
  - 计算 WTI原油指数 / DCE豆油指数 的相对强弱
  - 当比值 z-score > 1.5 → 能源偏强，做多原油/做空豆油
  - 当比值 z-score < -1.5 → 农产品偏强，做空原油/做多豆油

【子系统B】板块轮动信号
  - 动量排名：各品种20日收益率排序
  - 做多动量最强品种，做空动量最弱品种（等权对冲）

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOLS_ENERGY | 原油、燃料油 | 能源品种 |
| SYMBOLS_AGRI | 豆油、棕榈油 | 农产品品种 |
| KLINE_DURATION | 60*60*24 | 日K线 |
| MOMENTUM_PERIOD | 20 | 动量周期 |
| LOOKBACK | 30 | z-score窗口 |
| Z_ENTRY | 1.5 | 入场z阈值 |
| LOT_SIZE | 1 | 开仓手数 |
| REBALANCE_DAYS | 5 | 轮动调仓周期 |

【风险提示】

- 跨市场对冲需关注汇率风险和宏观因素冲击
- 产业链联动关系可能发生结构性变化
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time

# ============ 参数配置 ============
# 能源板块
SYMBOLS_ENERGY = [
    "INE.sc2509",   # 原油
    "SHFE.bu2510",  # 燃料油
]
# 农产品板块
SYMBOLS_AGRI = [
    "DCE.y2509",    # 豆油
    "DCE.p2509",    # 棕榈油
]
# 全品种列表
ALL_SYMBOLS = SYMBOLS_ENERGY + SYMBOLS_AGRI

KLINE_DURATION = 60 * 60 * 24   # 日K线
MOMENTUM_PERIOD = 20            # 动量计算周期
LOOKBACK = 30                   # z-score历史窗口
Z_ENTRY = 1.5                   # 入场z阈值
Z_EXIT = 0.3                   # 出场z阈值
LOT_SIZE = 1                    # 开仓手数
REBALANCE_DAYS = 5              # 调仓周期（交易日）
CLOSE_TIME = time(14, 55)       # 收盘前平仓


class EnergyAgriHedgeStrategy:
    """能源-农产品跨市场对冲与轮动策略"""

    def __init__(self, api):
        self.api = api
        self.hedge_positions = {}   # symbol -> position side
        self.last_rebalance_day = None
        self.rebalance_counter = 0

    def get_momentum(self, symbol, period=MOMENTUM_PERIOD):
        """计算品种动量（区间收益率）"""
        try:
            kl = self.api.get_kline_serial(symbol, KLINE_DURATION, period + 2)
            if len(kl) < period + 1:
                return 0
            prices = kl['close'].values
            momentum = (prices[-1] - prices[-period]) / prices[-period]
            return momentum
        except Exception as e:
            print(f"动量计算失败 {symbol}: {e}")
            return 0

    def calculate_relative_strength(self, energy_sym, agri_sym, lookback=LOOKBACK):
        """计算能源/农产品相对强弱（价比动量差）"""
        try:
            kl_e = self.api.get_kline_serial(energy_sym, KLINE_DURATION, lookback + 5)
            kl_a = self.api.get_kline_serial(agri_sym, KLINE_DURATION, lookback + 5)
            if len(kl_e) < lookback + 1 or len(kl_a) < lookback + 1:
                return 0, 0
            ret_e = np.diff(kl_e['close'].values[-lookback - 1:]) / kl_e['close'].values[-lookback - 1:-1]
            ret_a = np.diff(kl_a['close'].values[-lookback - 1:]) / kl_a['close'].values[-lookback - 1:-1]
            # 相对强弱 = 能源累计收益 - 农产品累计收益
            rel_strength = np.sum(ret_e) - np.sum(ret_a)
            return rel_strength, np.std(ret_e - ret_a)
        except Exception as e:
            print(f"相对强弱计算失败: {e}")
            return 0, 0

    def rank_all(self):
        """对所有品种按动量排名"""
        rankings = []
        for sym in ALL_SYMBOLS:
            mom = self.get_momentum(sym)
            rankings.append({'symbol': sym, 'momentum': mom})
            print(f"[{sym}] 20日动量: {mom*100:.2f}%")
        rankings.sort(key=lambda x: x['momentum'], reverse=True)
        return rankings

    def normalize_positions(self):
        """品种轮动：做多最强，做空最弱"""
        rankings = self.rank_all()
        if len(rankings) < 2:
            return
        best = rankings[0]
        worst = rankings[-1]

        # 平掉不在目标列表的仓位
        for sym in list(self.hedge_positions.keys()):
            if sym not in [best['symbol'], worst['symbol']]:
                self.close_position(sym)
                del self.hedge_positions[sym]

        # 做多最强
        if self.hedge_positions.get(best['symbol']) != 1:
            self.close_position(best['symbol'])
            self.open_long(best['symbol'])
            self.hedge_positions[best['symbol']] = 1
            print(f"[{datetime.now()}] 做多最强: {best['symbol']} (动量={best['momentum']*100:.2f}%)")

        # 做空最弱
        if self.hedge_positions.get(worst['symbol']) != -1:
            self.close_position(worst['symbol'])
            self.open_short(worst['symbol'])
            self.hedge_positions[worst['symbol']] = -1
            print(f"[{datetime.now()}] 做空最弱: {worst['symbol']} (动量={worst['momentum']*100:.2f}%)")

    def check_intermarket_hedge(self):
        """跨市场对冲检查（子系统A）"""
        # 原油 vs 豆油
        rel_e_y, vol = self.calculate_relative_strength(SYMBOLS_ENERGY[0], SYMBOLS_AGRI[0])
        z_e_y = rel_e_y / vol if vol > 0 else 0

        print(f"[跨市场] 原油-豆油相对强弱: {rel_e_y:.4f}, z={z_e_y:.3f}")

        if z_e_y > Z_ENTRY:
            # 能源偏强，对冲做多原油/做空豆油
            print(f"[跨市场信号] 能源偏强，入场做多原油/做空豆油")
            self.close_position(SYMBOLS_AGRI[0])
            self.open_long(SYMBOLS_ENERGY[0])
            self.open_short(SYMBOLS_AGRI[0])
        elif z_e_y < -Z_ENTRY:
            # 农产品偏强，对冲做空原油/做多豆油
            print(f"[跨市场信号] 农产品偏强，入场做空原油/做多豆油")
            self.close_position(SYMBOLS_ENERGY[0])
            self.open_short(SYMBOLS_ENERGY[0])
            self.open_long(SMBOLS_AGRI[0])
        elif abs(z_e_y) <= Z_EXIT:
            # 相对强弱回归，平掉对冲仓位
            self.close_position(SYMBOLS_ENERGY[0])
            self.close_position(SYMBOLS_AGRI[0])

    def open_long(self, symbol):
        """开多"""
        try:
            self.api.insert_order(symbol=symbol, direction="BUY", offset="OPEN", volume=LOT_SIZE)
        except Exception as e:
            print(f"开多失败 {symbol}: {e}")

    def open_short(self, symbol):
        """开空"""
        try:
            self.api.insert_order(symbol=symbol, direction="SELL", offset="OPEN", volume=LOT_SIZE)
        except Exception as e:
            print(f"开空失败 {symbol}: {e}")

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
        for sym in list(self.hedge_positions.keys()):
            self.close_position(sym)
        self.hedge_positions.clear()
        print(f"[{datetime.now()}] 收盘前全部平仓")

    def run(self):
        """运行策略"""
        print("=" * 60)
        print("能源-农产品跨市场对冲与品种轮动策略启动")
        print("子系统A: 原油-豆油跨市场对冲")
        print("子系统B: 四品种动量轮动")
        print(f"轮动调仓周期: {REBALANCE_DAYS}个交易日")
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

                # 子系统A：跨市场对冲
                self.check_intermarket_hedge()

                # 子系统B：品种轮动（每REBALANCE_DAYS天）
                if self.rebalance_counter % REBALANCE_DAYS == 1:
                    print(f"[{today}] 执行品种轮动调仓...")
                    self.normalize_positions()


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    # 模拟测试
    # api = TqApi(auth=TqSim())

    try:
        strategy = EnergyAgriHedgeStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
