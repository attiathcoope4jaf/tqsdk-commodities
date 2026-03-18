#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 25
策略名称: 农产品三品种跨周期动量策略
生成日期: 2026-03-18
仓库地址: tqsdk-commodities
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个跨周期共振策略，同时监控豆粕、玉米、棉花三个农产品品种，
在日线和4小时线两个周期上寻找共振动量信号。只有当日线和4小时线
动量方向一致时，才入场交易，提高信号可靠性。

策略逻辑：
1. 计算各品种日线和4小时线的动量（20日/4小时周期）
2. 当两个周期动量方向一致且强度超过阈值时入场
3. 做多动量最强的品种，做空动量最弱的品种
4. 每周一开盘重新评估，月度换仓

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOLS | 农产品3品种 | 交易品种列表 |
| DAILY_MOMENTUM | 20 | 日线动量周期 |
| H4_MOMENTUM | 24 | 4小时动量周期（24根4h K线） |
| MOMENTUM_THRESHOLD | 0.02 | 动量入场阈值 |
| LOT_SIZE | 1 | 单品种开仓手数 |
| REBALANCE_DAYS | 5 | 调仓周期（交易日） |

【风险提示】

- 跨周期策略信号较少，但可靠性较高
- 农产品受季节性和政策影响较大
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
    "ZCE.CF509",     # 棉花
]
DAILY_KLINE_DURATION = 60 * 60 * 24      # 日K线
H4_KLINE_DURATION = 60 * 60 * 4           # 4小时K线
DAILY_MOMENTUM = 20                       # 日线动量周期
H4_MOMENTUM = 24                          # 4小时线动量周期（24根4h K线）
MOMENTUM_THRESHOLD = 0.02                # 动量入场阈值
LOT_SIZE = 1                              # 单品种开仓手数
REBALANCE_DAYS = 5                        # 调仓周期（交易日）
CLOSE_TIME = time(14, 55)                 # 强平时间


class MultiTimeframeMomentumStrategy:
    def __init__(self, api):
        self.api = api
        self.positions = {}      # symbol -> position
        self.last_rebalance_date = None
        self.rebalance_counter = 0
        
    def calculate_momentum(self, symbol, duration_seconds, period):
        """计算指定周期K线的动量"""
        try:
            klines = self.api.get_kline_serial(symbol, duration_seconds, period + 1)
            if len(klines) < period + 1:
                return 0, 0
            closes = klines['close'].values
            daily_return = (closes[-1] - closes[-2]) / closes[-2] if len(closes) >= 2 else 0
            momentum = (closes[-1] - closes[0]) / closes[0]
            return momentum, daily_return
        except Exception:
            return 0, 0
            
    def calculate_volatility(self, symbol, duration_seconds, period=20):
        """计算波动率"""
        try:
            klines = self.api.get_kline_serial(symbol, duration_seconds, period)
            if len(klines) < period:
                return 1.0
            returns = np.diff(klines['close'].values) / klines['close'].values[:-1]
            return np.std(returns) if len(returns) > 0 else 1.0
        except Exception:
            return 1.0
            
    def rank_symbols(self):
        """对品种进行动量排名"""
        rankings = []
        for sym in SYMBOLS:
            daily_mom, daily_ret = self.calculate_momentum(sym, DAILY_KLINE_DURATION, DAILY_MOMENTUM)
            h4_mom, h4_ret = self.calculate_momentum(sym, H4_KLINE_DURATION, H4_MOMENTUM)
            vol = self.calculate_volatility(sym, DAILY_KLINE_DURATION)
            
            # 风险调整动量（动量/波动率）
            risk_adjusted_daily = daily_mom / vol if vol > 0 else 0
            risk_adjusted_h4 = h4_mom / vol if vol > 0 else 0
            
            # 共振分数：两个周期方向一致时加分
            direction_score = 1.0 if (daily_mom * h4_mom > 0) else 0.3
            composite_score = (risk_adjusted_daily + risk_adjusted_h4) * direction_score
            
            rankings.append({
                'symbol': sym,
                'daily_momentum': daily_mom,
                'h4_momentum': h4_mom,
                'volatility': vol,
                'composite_score': composite_score,
                'direction_aligned': daily_mom * h4_mom > 0
            })
            print(f"[{sym}] 日线动量:{daily_mom:.4f} 4H动量:{h4_mom:.4f} 共振:{direction_score:.1f} 综合:{composite_score:.4f}")
        
        rankings.sort(key=lambda x: x['composite_score'], reverse=True)
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
        print("农产品跨周期动量策略启动")
        print("=" * 60)
        
        quote_0 = self.api.get_quote(SYMBOLS[0])
        last_trade_date = None
        
        while True:
            self.api.wait_update()
            
            # 检查是否需要每日评估
            now = datetime.now()
            trade_date = now.strftime("%Y-%m-%d")
            
            # 强平检查
            current_time = now.time()
            if current_time >= CLOSE_TIME:
                self.close_all_positions()
                continue
                
            # 每5个交易日或新的一天重新评估
            if last_trade_date != trade_date:
                last_trade_date = trade_date
                self.rebalance_counter += 1
                
                if self.rebalance_counter % REBALANCE_DAYS == 1:
                    print(f"\n[{trade_date}] 开始重新评估...")
                    rankings = self.rank_symbols()
                    
                    # 先平掉不在持仓列表的仓位
                    current_holds = [k for k, v in self.positions.items() if v != 0]
                    target_symbols = set(r['symbol'] for r in rankings)
                    
                    for held in current_holds:
                        if held not in target_symbols:
                            self.close_all(held)
                            
                    # 做多动量最强，做空动量最弱
                    if len(rankings) >= 2:
                        best = rankings[0]
                        worst = rankings[-1]
                        
                        # 做多最强
                        if best['direction_aligned'] and best['composite_score'] > MOMENTUM_THRESHOLD:
                            self.open_long(best['symbol'])
                            self.positions[best['symbol']] = 1
                        else:
                            self.close_all(best['symbol'])
                            
                        # 做空最弱
                        if worst['direction_aligned'] and worst['composite_score'] > MOMENTUM_THRESHOLD:
                            self.open_short(worst['symbol'])
                            self.positions[worst['symbol']] = -1
                        else:
                            self.close_all(worst['symbol'])


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 模拟测试
    # api = TqApi(auth=TqSim())
    
    try:
        strategy = MultiTimeframeMomentumStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
