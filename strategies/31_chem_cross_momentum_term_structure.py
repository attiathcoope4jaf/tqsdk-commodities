"""
策略31: 化工系截面动量与期限结构择时策略
品种: 化工系（甲醇MA、塑料L、聚丙烯PP、PTA、沥青BU）
核心思路: 结合截面动量和期限结构两个维度
  - 维度1: 20日动量截面排名
  - 维度2: 近远月价差（期限结构）方向
  综合打分后做多最强+做空最弱，每周调仓一次
作者: TqSdk量化团队
"""

import tenday
import numpy as np
import pandas as pd
from datetime import datetime

# ========== 配置 ==========
UNIVERSE = {
    "MA": "CZCE.MA",     # 甲醇
    "L":  "DCE.L",       # 塑料
    "PP": "DCE.PP",      # 聚丙烯
    "TA": "CZCE.TA",     # PTA
    "BU": "INE.BU",      # 沥青
}

POSITION_SIZE = 1        # 每品种开仓手数
REBALANCE_INTERVALS = 5  # 调仓间隔（bar数，1min bar，约5个交易日）
VOLATILITYLookback = 20  # 波动率计算窗口

# ========== 主策略 ==========
class ChemCrossSectionStrategy:
    def __init__(self, api):
        self.api = api
        self.klines = {}
        self.positions = {}
        self.daily_scores = {}   # 综合打分
        self.last_rebalance_time = None
        self.rebalance_count = 0

        # 订阅所有品种的1min K线
        for name, symbol in UNIVERSE.items():
            self.klines[name] = api.get_kline_serial(symbol, 60)
            self.positions[name] = 0

        print(f"[初始化] 化工系截面动量策略已启动，监控品种: {list(UNIVERSE.keys())}")

    def calc_momentum(self, kline, period=20):
        """计算N日收益率作为动量因子"""
        if len(kline) < period + 1:
            return np.nan
        close = kline["close"].values
        return (close[-1] / close[-period - 1]) - 1

    def calc_term_structure(self, kline, near_period=5, far_period=20):
        """计算期限结构因子：近月涨幅 vs 远月涨幅"""
        if len(kline) < far_period + 1:
            return np.nan
        close = kline["close"].values
        near_ret = (close[-1] / close[-near_period - 1]) - 1
        far_ret = (close[-near_period - 1] / close[-far_period - 1]) - 1
        return near_ret - far_ret  # 近月强为正，贴水结构为负

    def calc_volatility(self, kline, period=20):
        """计算历史波动率用于仓位调整"""
        if len(kline) < period + 1:
            return np.nan
        returns = np.diff(np.log(kline["close"].values[-period:]))
        return np.std(returns) * np.sqrt(252 * 240)  # 年化波动率（1min周期）

    def rank_cross_section(self):
        """截面排名打分，0-100"""
        scores = {}
        momentums = {}
        term_structures = {}

        for name, kline in self.klines.items():
            m = self.calc_momentum(kline)
            t = self.calc_term_structure(kline)
            v = self.calc_volatility(kline)
            if np.isnan(m) or np.isnan(t) or np.isnan(v):
                continue
            momentums[name] = m
            term_structures[name] = t
            scores[name] = 0

        if len(scores) < 2:
            return {}

        # 动量因子排名（越大越强）
        mom_series = pd.Series(momentums)
        mom_rank = mom_series.rank(pct=True)

        # 期限结构因子排名（近月强=正spread）
        ts_series = pd.Series(term_structures)
        ts_rank = ts_series.rank(pct=True)

        # 综合打分：动量权重60%，期限结构权重40%
        final_scores = {}
        for name in scores:
            final_scores[name] = 0.6 * mom_rank[name] + 0.4 * ts_rank[name]

        return final_scores

    def rebalance(self, scores):
        """根据截面排名调仓：做多最强，做空最弱"""
        if len(scores) < 2:
            return

        # 关闭所有现有持仓
        for name in self.positions:
            if self.positions[name] != 0:
                self.close_position(name)
                self.positions[name] = 0

        sorted_names = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        winner = sorted_names[0][0]   # 动量最强
        loser = sorted_names[-1][0]    # 动量最弱

        # 做多最强品种
        self.api.insert_order(
            symbol=UNIVERSE[winner],
            direction="BUY",
            offset="OPEN",
            volume=self.positions.get(winner, 0) + POSITION_SIZE,
            limit_price=0,
            position_effect=POSITION_SIZE
        )
        self.positions[winner] = POSITION_SIZE
        print(f"[调仓] 做多 {winner}，做空 {loser}，截面打分: {sorted_names}")

        # 做空最弱品种（如果品种不同）
        if loser != winner:
            self.api.insert_order(
                symbol=UNIVERSE[loser],
                direction="SELL",
                offset="OPEN",
                volume=self.positions.get(loser, 0) + POSITION_SIZE,
                limit_price=0,
                position_effect=POSITION_SIZE
            )
            self.positions[loser] = -POSITION_SIZE

    def close_position(self, name):
        symbol = UNIVERSE[name]
        pos = self.positions.get(name, 0)
        if pos > 0:
            self.api.insert_order(symbol=symbol, direction="SELL", offset="CLOSE",
                                  volume=abs(pos), limit_price=0)
        elif pos < 0:
            self.api.insert_order(symbol=symbol, direction="BUY", offset="CLOSE",
                                  volume=abs(pos), limit_price=0)

    def check_forced_close(self):
        """14:55 强制全部平仓（不持隔夜）"""
        dt = datetime.now()
        if dt.hour == 14 and dt.minute >= 55:
            for name in self.positions:
                if self.positions[name] != 0:
                    self.close_position(name)
                    self.positions[name] = 0
                    print(f"[强平] {name} 持仓已平仓")

    def on_bar(self):
        """每分钟执行的调仓检查"""
        dt = datetime.now()
        # 跳过集合竞价和刚开盘时段
        if dt.hour < 9 or (dt.hour == 9 and dt.minute < 15):
            return
        if dt.hour >= 14 and dt.minute >= 55:
            self.check_forced_close()
            return

        # 定时调仓
        self.rebalance_count += 1
        if self.rebalance_count % REBALANCE_INTERVALS == 0:
            scores = self.rank_cross_section()
            if scores:
                self.rebalance(scores)
                self.rebalance_count = 0


# ========== TqSdk 入口 ==========
def main():
    from tqsdk import TqApi, TqSim
    api = TqApi(account=TqSim())
    strategy = ChemCrossSectionStrategy(api)

    # 主循环
    while True:
        api.wait_update()
        if api.is_changing(strategy.klines[list(UNIVERSE.keys())[0]], "last"):
            strategy.on_bar()


if __name__ == "__main__":
    main()
