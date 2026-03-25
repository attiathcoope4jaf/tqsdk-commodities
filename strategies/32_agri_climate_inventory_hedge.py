"""
策略32: 农产品气候因子与库存周期对冲策略
品种: 农产品系（豆粕m、豆油y、玉米c、棉花cf、白糖sr）
核心思路:
  - 因子1: 20日动量（趋势因子）
  - 因子2: 30日库存周期代理（成交量/持仓量变化率）
  - 因子3: 布林带宽度（波动率突破因子）
  三因子等权打分，买入最强、卖出最弱，每周调仓
作者: TqSdk量化团队
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ========== 配置 ==========
UNIVERSE = {
    "m":  "DCE.m",       # 豆粕
    "y":  "DCE.y",       # 豆油
    "c":  "DCE.c",       # 玉米
    "cf": "CZCE.CF",     # 棉花
    "sr": "CZCE.SR",     # 白糖
}

POSITION_SIZE = 1
REBALANCE_BARS = 5   # 约每周调仓一次（1min bar）

class AgriClimateInventoryStrategy:
    def __init__(self, api):
        self.api = api
        self.klines = {}
        self.positions = {}
        self.rebalance_count = 0

        for name, symbol in UNIVERSE.items():
            self.klines[name] = api.get_kline_serial(symbol, 60)
            self.positions[name] = 0

        print(f"[初始化] 农产品气候因子与库存周期策略已启动，品种: {list(UNIVERSE.keys())}")

    def calc_momentum(self, kline, period=20):
        """20日动量因子"""
        if len(kline) < period + 1:
            return np.nan
        close = kline["close"].values
        return (close[-1] / close[-period - 1]) - 1

    def calc_inventory_cycle(self, kline, period=30):
        """库存周期代理：成交量+持仓量综合变化率"""
        if len(kline) < period + 1:
            return np.nan
        vol = kline["volume"].values[-period:]
        oi = kline["open_interest"].values[-period:]
        vol_chg = (vol[-1] / vol[0]) - 1 if vol[0] > 0 else 0
        oi_chg = (oi[-1] / oi[0]) - 1 if oi[0] > 0 else 0
        # 库存增加（成交量持仓量增加）= 被动去库或主动累库，通常价格有压力
        # 库存减少（成交持仓萎缩）= 被动累库或主动去库，通常价格有支撑
        return -(vol_chg * 0.5 + oi_chg * 0.5)  # 取负，库存低=因子值高

    def calc_boll_width(self, kline, period=20):
        """布林带宽度因子：波动率收缩后扩张"""
        if len(kline) < period + 1:
            return np.nan
        close = kline["close"].values[-period:]
        mid = np.mean(close)
        std = np.std(close)
        width = std / mid if mid != 0 else 0
        return width

    def rank_factors(self):
        """三因子截面打分"""
        factor_data = {}
        for name, kline in self.klines.items():
            mom = self.calc_momentum(kline)
            inv = self.calc_inventory_cycle(kline)
            bw  = self.calc_boll_width(kline)
            if np.isnan(mom) or np.isnan(inv) or np.isnan(bw):
                continue
            factor_data[name] = {"momentum": mom, "inventory": inv, "bandwidth": bw}

        if len(factor_data) < 2:
            return {}

        df = pd.DataFrame(factor_data).T
        # 动量：越高越好；库存周期：越低越好（负相关）；布林宽度：越高越好（突破概率大）
        rank_mom  = df["momentum"].rank(pct=True)
        rank_inv  = df["inventory"].rank(pct=True)
        rank_bw   = df["bandwidth"].rank(pct=True)

        # 等权综合
        final_scores = {}
        for name in df.index:
            final_scores[name] = (rank_mom[name] + (1 - rank_inv[name]) + rank_bw[name]) / 3

        return final_scores

    def rebalance(self, scores):
        """调仓：做多最强 + 做空最弱"""
        for name in self.positions:
            if self.positions[name] != 0:
                self._close(name)
                self.positions[name] = 0

        sorted_names = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        winner = sorted_names[0][0]
        loser  = sorted_names[-1][0]

        self.api.insert_order(
            symbol=UNIVERSE[winner], direction="BUY", offset="OPEN",
            volume=POSITION_SIZE, limit_price=0
        )
        self.positions[winner] = POSITION_SIZE

        if loser != winner:
            self.api.insert_order(
                symbol=UNIVERSE[loser], direction="SELL", offset="OPEN",
                volume=POSITION_SIZE, limit_price=0
            )
            self.positions[loser] = -POSITION_SIZE

        print(f"[调仓] 做多{winner} 做空{loser}，综合打分: {sorted_names}")

    def _close(self, name):
        pos = self.positions[name]
        if pos > 0:
            self.api.insert_order(symbol=UNIVERSE[name], direction="SELL", offset="CLOSE",
                                   volume=abs(pos), limit_price=0)
        elif pos < 0:
            self.api.insert_order(symbol=UNIVERSE[name], direction="BUY", offset="CLOSE",
                                   volume=abs(pos), limit_price=0)

    def on_bar(self):
        dt = datetime.now()
        if dt.hour < 9 or (dt.hour == 9 and dt.minute < 15):
            return
        if dt.hour >= 14 and dt.minute >= 55:
            for name in self.positions:
                if self.positions[name] != 0:
                    self._close(name)
                    self.positions[name] = 0
            return

        self.rebalance_count += 1
        if self.rebalance_count % REBALANCE_BARS == 0:
            scores = self.rank_factors()
            if scores:
                self.rebalance(scores)
                self.rebalance_count = 0


def main():
    from tqsdk import TqApi, TqSim
    api = TqApi(account=TqSim())
    strategy = AgriClimateInventoryStrategy(api)
    while True:
        api.wait_update()
        if api.is_changing(strategy.klines[list(UNIVERSE.keys())[0]], "last"):
            strategy.on_bar()


if __name__ == "__main__":
    main()
