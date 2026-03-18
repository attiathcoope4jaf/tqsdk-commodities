#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 26
策略名称: 商品期货六品种多因子截面策略
生成日期: 2026-03-18
仓库地址: tqsdk-commodities
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个多因子截面策略，同时监控铜、铝、锌、螺纹钢、热卷、铁矿石
六个品种，基于三个因子综合打分进行截面排序，做多Top品种，做空Bottom品种。

三个因子：
1. 动量因子（20日收益率）
2. 波动率因子（20日收益标准差的倒数，做多低波动）
3. 趋势强度因子（均线多头排列程度）

策略逻辑：
1. 每日收盘后计算各品种三个因子分数
2. 综合打分后排序
3. 做多排名Top1，做空排名Bottom1
4. 每周一开盘调仓

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOLS | 6品种 | 交易品种列表 |
| MOMENTUM_PERIOD | 20 | 动量因子周期 |
| VOLATILITY_PERIOD | 20 | 波动率因子周期 |
| MA_SHORT | 10 | 短期均线 |
| MA_LONG | 60 | 长期均线 |
| LOT_SIZE | 1 | 单品种开仓手数 |
| REBALANCE_DAYS | 5 | 调仓周期 |

【风险提示】

- 多因子策略需关注因子失效风险
- 截面策略在趋势行情中表现较好
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time


# ============ 参数配置 ============
SYMBOLS = [
    "SHFE.cu2510",   # 铜
    "SHFE.al2510",   # 铝
    "SHFE.zn2510",   # 锌
    "SHFE.rb2510",   # 螺纹钢
    "SHFE.hc2510",   # 热卷
    "DCE.i2509",     # 铁矿石
]
KLINE_DURATION = 60 * 60 * 24       # 日K线
MOMENTUM_PERIOD = 20                # 动量因子周期
VOLATILITY_PERIOD = 20              # 波动率因子周期
MA_SHORT = 10                       # 短期均线
MA_LONG = 60                        # 长期均线
LOT_SIZE = 1                        # 单品种开仓手数
REBALANCE_DAYS = 5                  # 调仓周期
CLOSE_TIME = time(14, 55)           # 强平时间


class MultiFactorCrossSectionStrategy:
    def __init__(self, api):
        self.api = api
        self.positions = {}      # symbol -> position (1=多, -1=空)
        self.last_rebalance_date = None
        self.rebalance_counter = 0
        
    def calculate_factors(self, symbol):
        """计算三因子"""
        try:
            # 动量因子
            klines = self.api.get_kline_serial(symbol, KLINE_DURATION, MOMENTUM_PERIOD + MA_LONG + 1)
            if len(klines) < MOMENTUM_PERIOD + 1:
                return None
            closes = klines['close'].values
            momentum = (closes[-1] - closes[-MOMENTUM_PERIOD]) / closes[-MOMENTUM_PERIOD]
            
            # 波动率因子（低波动=高分数）
            returns = np.diff(closes[-VOLATILITY_PERIOD:]) / closes[-VOLATILITY_PERIOD:-1]
            volatility = np.std(returns) if len(returns) > 0 else 1.0
            vol_factor = 1.0 / volatility if volatility > 0 else 0
            
            # 趋势强度因子（短期均线 > 长期均线 -> 强趋势）
            if len(closes) >= MA_LONG:
                ma_s = np.mean(closes[-MA_SHORT:])
                ma_l = np.mean(closes[-MA_LONG:])
                trend_factor = (ma_s - ma_l) / ma_l if ma_l > 0 else 0
            else:
                trend_factor = 0
                
            return {
                'momentum': momentum,
                'vol_factor': vol_factor,
                'trend_factor': trend_factor
            }
        except Exception as e:
            print(f"因子计算失败 {symbol}: {e}")
            return None
            
    def normalize_factor(self, factor_values):
        """Z-score标准化因子"""
        values = list(factor_values.values())
        if len(values) < 2:
            return factor_values
        mean_val = np.mean(values)
        std_val = np.std(values)
        if std_val == 0:
            return {k: 0 for k in factor_values}
        return {k: (v - mean_val) / std_val for k, v in factor_values.items()}
            
    def rank_symbols(self):
        """综合因子排名"""
        raw_factors = {}
        for sym in SYMBOLS:
            factors = self.calculate_factors(sym)
            if factors:
                raw_factors[sym] = factors
                
        if len(raw_factors) < 2:
            return []
            
        # 标准化各因子
        mom_values = {s: f['momentum'] for s, f in raw_factors.items()}
        vol_values = {s: f['vol_factor'] for s, f in raw_factors.items()}
        trd_values = {s: f['trend_factor'] for s, f in raw_factors.items()}
        
        mom_norm = self.normalize_factor(mom_values)
        vol_norm = self.normalize_factor(vol_values)
        trd_norm = self.normalize_factor(trd_values)
        
        # 综合打分（权重：动量40%，波动率30%，趋势30%）
        rankings = []
        for sym in raw_factors:
            composite = 0.4 * mom_norm.get(sym, 0) + 0.3 * vol_norm.get(sym, 0) + 0.3 * trd_norm.get(sym, 0)
            rankings.append({
                'symbol': sym,
                'momentum': raw_factors[sym]['momentum'],
                'vol_factor': raw_factors[sym]['vol_factor'],
                'trend_factor': raw_factors[sym]['trend_factor'],
                'composite': composite
            })
            print(f"[{sym}] 动量:{raw_factors[sym]['momentum']:.4f} 低波:{raw_factors[sym]['vol_factor']:.4f} 趋势:{raw_factors[sym]['trend_factor']:.4f} 综合:{composite:.4f}")
            
        rankings.sort(key=lambda x: x['composite'], reverse=True)
        return rankings
        
    def open_long(self, symbol):
        """开多仓"""
        try:
            pos = self.api.get_position(symbol)
            if abs(pos.pos_long) < LOT_SIZE:
                self.api.insert_order(symbol=symbol, direction="BUY", offset="OPEN", volume=LOT_SIZE)
                print(f"[{datetime.now()}] 开多 {symbol}")
        except Exception as e:
            print(f"开多失败 {symbol}: {e}")
            
    def open_short(self, symbol):
        """开空仓"""
        try:
            pos = self.api.get_position(symbol)
            if abs(pos.pos_short) < LOT_SIZE:
                self.api.insert_order(symbol=symbol, direction="SELL", offset="OPEN", volume=LOT_SIZE)
                print(f"[{datetime.now()}] 开空 {symbol}")
        except Exception as e:
            print(f"开空失败 {symbol}: {e}")
            
    def close_all(self, symbol):
        """平仓"""
        try:
            pos = self.api.get_position(symbol)
            if pos.pos_long > 0:
                self.api.insert_order(symbol=symbol, direction="SELL", offset="CLOSE", volume=pos.pos_long)
                print(f"[{datetime.now()}] 平多 {symbol}")
            if pos.pos_short > 0:
                self.api.insert_order(symbol=symbol, direction="BUY", offset="CLOSE", volume=pos.pos_short)
                print(f"[{datetime.now()}] 平空 {symbol}")
        except Exception as e:
            print(f"平仓失败 {symbol}: {e}")
            
    def close_all_positions(self):
        """平所有仓"""
        for sym in SYMBOLS:
            self.close_all(sym)
            
    def run(self):
        """主运行循环"""
        print("=" * 60)
        print("商品期货多因子截面策略启动")
        print("=" * 60)
        
        last_trade_date = None
        
        while True:
            self.api.wait_update()
            
            now = datetime.now()
            trade_date = now.strftime("%Y-%m-%d")
            
            # 强平检查
            if now.time() >= CLOSE_TIME:
                self.close_all_positions()
                continue
                
            # 每日评估
            if last_trade_date != trade_date:
                last_trade_date = trade_date
                self.rebalance_counter += 1
                
                if self.rebalance_counter % REBALANCE_DAYS == 1:
                    print(f"\n[{trade_date}] 开始因子分析...")
                    rankings = self.rank_symbols()
                    
                    if len(rankings) >= 2:
                        best = rankings[0]
                        worst = rankings[-1]
                        
                        # 先清掉不在目标列表的仓位
                        current_symbols = set(self.positions.keys())
                        target_symbols = {best['symbol'], worst['symbol']}
                        
                        for sym in current_symbols:
                            if sym not in target_symbols:
                                self.close_all(sym)
                                del self.positions[sym]
                                
                        # 做多最强
                        if self.positions.get(best['symbol']) != 1:
                            self.close_all(best['symbol'])
                            self.open_long(best['symbol'])
                            self.positions[best['symbol']] = 1
                            
                        # 做空最弱
                        if self.positions.get(worst['symbol']) != -1:
                            self.close_all(worst['symbol'])
                            self.open_short(worst['symbol'])
                            self.positions[worst['symbol']] = -1


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 模拟测试
    # api = TqApi(auth=TqSim())
    
    try:
        strategy = MultiFactorCrossSectionStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
