#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 27
策略名称: 有色金属跨期价差与Carry套利策略
生成日期: 2026-03-23
仓库地址: tqsdk-commodities
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略综合运用两种套利思路：

【Part A · 跨期价差套利】
对有色金属（铜、铝、锌）的近月-远月合约进行跨期套利。
在商品期货中，当市场处于正向市场（Contango，现货<期货），近月合约往往升水；
当市场处于反向市场（Backwardation，现货>期货），近月合约贴水。
通过捕捉近远月价差的均值回归进行套利。

【Part B · Carry套利（移仓收益策略）】
期货合约持有期间存在"升水收益"——当市场为正向市场时，远月价格高于近月，
持有远月合约并定期向更远月移仓，可以获得稳定的移仓收益（正Carry）。
本策略监控沪铜主力合约的近远月价差，判断市场结构并择机建仓。

策略逻辑：
1. 监控 CU/Symbol 近月-次近月价差的 z-score
2. z-score > 1.5 → 价差偏高，做空近月/做多远月（预期收敛）
3. z-score < -1.5 → 价差偏低，做多近月/做空远月（预期回归）
4. 当市场正向结构（近低远高）且稳定时，持续持有正Carry仓位

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOL_NEAR | SHFE.cu2510 | 近月合约 |
| SYMBOL_FAR | SHFE.cu2601 | 远月合约 |
| AL_NEAR | SHFE.al2510 | 铝近月 |
| AL_FAR | SHFE.al2601 | 铝远月 |
| ZN_NEAR | SHFE.zn2510 | 锌近月 |
| ZN_FAR | SHFE.zn2601 | 锌远月 |
| KLINE_DURATION | 60*60*24 | 日K线 |
| LOOKBACK | 30 | 价差窗口 |
| Z_ENTRY | 1.5 | 入场z阈值 |
| Z_EXIT | 0.3 | 出场z阈值 |
| LOT_SIZE | 1 | 开仓手数 |
| CLOSE_TIME | time(14,55) | 收盘前平仓 |

【风险提示】

- 跨期套利需关注流动性风险，近远月合约成交量差异较大
- 市场结构切换（Contango→Backwardation）可能导致Carry策略亏损
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time

# ============ 参数配置 ============
# 沪铜跨期
CU_NEAR = "SHFE.cu2510"
CU_FAR = "SHFE.cu2601"
# 沪铝跨期
AL_NEAR = "SHFE.al2510"
AL_FAR = "SHFE.al2601"
# 沪锌跨期
ZN_NEAR = "SHFE.zn2510"
ZN_FAR = "SHFE.zn2601"

KLINE_DURATION = 60 * 60 * 24   # 日K线
LOOKBACK = 30                   # 价差历史窗口
Z_ENTRY = 1.5                  # 入场z阈值
Z_EXIT = 0.3                   # 出场z阈值
LOT_SIZE = 1                   # 开仓手数
CLOSE_TIME = time(14, 55)      # 收盘前平仓时间


class CarryArbitrageStrategy:
    """跨期价差与Carry套利策略"""

    def __init__(self, api):
        self.api = api
        self.positions = {}    # {(near, far): position_side}
        self.z_scores = {}     # pair -> current z-score

    def get_spread(self, sym_near, sym_far, n=LOOKBACK + 5):
        """获取近远月价差序列"""
        try:
            kl_near = self.api.get_kline_serial(sym_near, KLINE_DURATION, n)
            kl_far = self.api.get_kline_serial(sym_far, KLINE_DURATION, n)
            if len(kl_near) < n or len(kl_far) < n:
                return []
            # 价差 = 近月价格 - 远月价格（正数=近月贴水，负数=近月升水）
            spread = kl_near['close'].values - kl_far['close'].values
            return spread
        except Exception as e:
            print(f"获取价差失败 {sym_near}-{sym_far}: {e}")
            return []

    def calculate_z(self, spread):
        """计算价差z-score"""
        if len(spread) < LOOKBACK:
            return 0
        window = spread[-LOOKBACK:]
        mean = np.mean(window)
        std = np.std(window)
        if std == 0:
            return 0
        z = (spread[-1] - mean) / std
        return z

    def open_carry(self, sym_near, sym_far, direction, pair_name):
        """开设跨期仓位
        direction > 0: 近月-远月价差偏低，做多价差（买近卖远）
        direction < 0: 近月-远月价差偏高，做空价差（卖近买远）
        """
        try:
            if direction > 0:
                # 做多价差：买近月合约（预期近月涨幅大于远月）
                self.api.insert_order(symbol=sym_near, direction="BUY", offset="OPEN", volume=LOT_SIZE)
                # 做空价差：卖远月合约
                self.api.insert_order(symbol=sym_far, direction="SELL", offset="OPEN", volume=LOT_SIZE)
                self.positions[(sym_near, sym_far)] = 1
                print(f"[{datetime.now()}] [{pair_name}] 开仓: 做多价差(买近卖远)")
            else:
                # 做空价差：卖近月合约
                self.api.insert_order(symbol=sym_near, direction="SELL", offset="OPEN", volume=LOT_SIZE)
                # 做多价差：买远月合约
                self.api.insert_order(symbol=sym_far, direction="BUY", offset="OPEN", volume=LOT_SIZE)
                self.positions[(sym_near, sym_far)] = -1
                print(f"[{datetime.now()}] [{pair_name}] 开仓: 做空价差(卖近买远)")
        except Exception as e:
            print(f"开仓失败 [{pair_name}]: {e}")

    def close_carry(self, sym_near, sym_far, pair_name, reason=""):
        """平跨期仓位"""
        try:
            pos_near = self.api.get_position(sym_near)
            pos_far = self.api.get_position(sym_far)
            if pos_near.pos_long > 0:
                self.api.insert_order(symbol=sym_near, direction="SELL", offset="CLOSE", volume=pos_near.pos_long)
            if pos_near.pos_short > 0:
                self.api.insert_order(symbol=sym_near, direction="BUY", offset="CLOSE", volume=pos_near.pos_short)
            if pos_far.pos_long > 0:
                self.api.insert_order(symbol=sym_far, direction="SELL", offset="CLOSE", volume=pos_far.pos_long)
            if pos_far.pos_short > 0:
                self.api.insert_order(symbol=sym_far, direction="BUY", offset="CLOSE", volume=pos_far.pos_short)
            print(f"[{datetime.now()}] [{pair_name}] 平仓: {reason}")
            del self.positions[(sym_near, sym_far)]
        except Exception as e:
            print(f"平仓失败 [{pair_name}]: {e}")

    def manage_pair(self, sym_near, sym_far, pair_name):
        """管理单个品种对"""
        spread = self.get_spread(sym_near, sym_far)
        if len(spread) < LOOKBACK:
            return
        z = self.calculate_z(spread)
        self.z_scores[(sym_near, sym_far)] = z
        key = (sym_near, sym_far)
        current_pos = self.positions.get(key, 0)

        # 入场逻辑
        if current_pos == 0:
            if z < -Z_ENTRY:
                # 价差偏低（近月相对便宜），做多价差
                self.open_carry(sym_near, sym_far, 1, pair_name)
            elif z > Z_ENTRY:
                # 价差偏高（近月相对贵），做空价差
                self.open_carry(sym_near, sym_far, -1, pair_name)
        else:
            # 持仓中：出场或止损
            z_change = abs(z - self.z_scores.get(key + ("entry",), [z])[0]) if key + ("entry",) in [(k + ("entry",)) for k in [key]] else 0
            # 简化为：回归到0附近即平仓
            if abs(z) <= Z_EXIT:
                self.close_carry(sym_near, sym_far, pair_name, "z-score回归")
            elif abs(z) > Z_ENTRY * 2:
                self.close_carry(sym_near, sym_far, pair_name, "z-score扩大止损")

    def close_all(self):
        """收盘前全部平仓"""
        for (near, far) in list(self.positions.keys()):
            pair = f"{near}-{far}"
            self.close_carry(near, far, pair, "收盘前强平")

    def run(self):
        """运行策略"""
        print("=" * 60)
        print("有色金属跨期价差与Carry套利策略启动")
        print("监控铜、铝、锌三组近远月合约的跨期套利机会")
        print(f"入场z阈值: {Z_ENTRY}, 出场z阈值: {Z_EXIT}")
        print("=" * 60)

        pairs = [
            (CU_NEAR, CU_FAR, "沪铜"),
            (AL_NEAR, AL_FAR, "沪铝"),
            (ZN_NEAR, ZN_FAR, "沪锌"),
        ]

        while True:
            self.api.wait_update()

            # 收盘前强平
            if datetime.now().time() >= CLOSE_TIME:
                self.close_all()
                print(f"[{datetime.now()}] 收盘前全部平仓，策略结束")
                break

            # 管理各品种对
            for near, far, name in pairs:
                self.manage_pair(near, far, name)
                spreads = self.get_spread(near, far)
                if len(spreads) >= LOOKBACK:
                    z = self.calculate_z(spreads)
                    current_spread = spreads[-1]
                    window_mean = np.mean(spreads[-LOOKBACK:])
                    print(f"[{name}] 价差={current_spread:.2f}(均值={window_mean:.2f}), z={z:.3f}, 持仓={self.positions.get((near, far), 0)}")


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    # 模拟测试
    # api = TqApi(auth=TqSim())

    try:
        strategy = CarryArbitrageStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
