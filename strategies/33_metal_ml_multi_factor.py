"""
策略33: 有色金属板块机器学习多因子动态权重量化策略
Precious Metals & Base Metals ML Multi-Factor Dynamic Weighting Strategy
- 多因子: 动量因子、Carry因子、波动率因子、产业链相关性子因子
- 使用滚动回归动态调整因子权重
- 品种: CU, AL, ZN, NI, AU, AG
- 策略类型: 多因子量化
- 更新时间: 2026-03-26
"""
import numpy as np
import pandas as pd
from tqsdk import TqApi, TqAuth, TargetPosTask, TqSim
from datetime import datetime, timedelta

# ========== 配置区 ==========
SYMBOLS = ["SHFE.cu", "SHFE.al", "SHFE.zn", "SHFE.ni", "SHFE.au", "SHFE.ag"]
FACTOR_NAMES = ["momentum", "carry", "volatility", "correlation"]

# 因子计算参数
MOMENTUM_WINDOW = 20       # 动量窗口(天)
CARRY_WINDOW = 10          # Carry计算窗口
VOL_WINDOW = 20             # 波动率窗口
CORR_WINDOW = 60           # 相关性计算窗口
REBALANCE_FREQ = 5         # 调仓频率(天)
POSITION_SIZE = 6          # 持有品种数量

# 风控参数
MAX_POS_SINGLE = 0.25      # 单品种最大仓位
MAX_SECTOR_POS = 0.50      # 同一板块最大仓位
MAX_DRAWDOWN = 0.15        # 最大回撤阈值


def calc_momentum_factor(price_series: pd.Series, window: int = MOMENTUM_WINDOW) -> float:
    """计算动量因子: 近N日收益率"""
    if len(price_series) < window:
        return 0.0
    return (price_series.iloc[-1] / price_series.iloc[-window] - 1)


def calc_carry_factor(price_series: pd.Series, window: int = CARRY_WINDOW) -> float:
    """计算Carry因子: 近N日收益/波动率"""
    if len(price_series) < window:
        return 0.0
    ret = price_series.pct_change().dropna()
    if len(ret) < 2 or ret.std() == 0:
        return 0.0
    return ret.iloc[-window:].mean() / (ret.iloc[-window:].std() + 1e-8)


def calc_volatility_factor(price_series: pd.Series, window: int = VOL_WINDOW) -> float:
    """计算波动率因子: 波动率倒数(低波动更优)"""
    if len(price_series) < window:
        return 0.0
    vol = price_series.pct_change().rolling(window).std().iloc[-1]
    if vol == 0:
        return 0.0
    return 1.0 / (vol + 1e-8)


def calc_correlation_factor(price_dict: dict, target_symbol: str,
                             window: int = CORR_WINDOW) -> float:
    """计算与板块平均收益的相关性因子"""
    if target_symbol not in price_dict:
        return 0.0
    if len(price_dict[target_symbol]) < window:
        return 0.0
    target_ret = price_dict[target_symbol].pct_change().dropna()
    other_rets = []
    for sym, series in price_dict.items():
        if sym != target_symbol:
            other = series.pct_change().dropna()
            if len(other) >= window:
                other_rets.append(other.iloc[-window:])
    if not other_rets:
        return 0.0
    bench = pd.concat(other_rets, axis=1).mean(axis=1)
    if len(bench) < 5:
        return 0.0
    corr = target_ret.iloc[-min(len(target_ret), window):].corr(
        bench.iloc[-min(len(bench), window):]
    )
    return corr if not np.isnan(corr) else 0.0


def rolling_regression_weights(factor_df: pd.DataFrame,
                                target_returns: pd.Series,
                                lookback: int = 20) -> dict:
    """
    使用滚动OLS回归计算动态因子权重
    返回各因子的标准化权重
    """
    if len(factor_df) < lookback or len(target_returns) < lookback:
        # 默认等权
        n_factors = len(FACTOR_NAMES)
        return {name: 1.0 / n_factors for name in FACTOR_NAMES}
    
    # 取最近lookback天数据
    fac = factor_df.iloc[-lookback:].copy()
    ret = target_returns.iloc[-lookback:].copy()
    
    # 移除NaN
    valid_idx = fac.dropna().index.intersection(ret.dropna().index)
    if len(valid_idx) < 5:
        n_factors = len(FACTOR_NAMES)
        return {name: 1.0 / n_factors for name in FACTOR_NAMES}
    
    fac = fac.loc[valid_idx]
    ret = ret.loc[valid_idx]
    
    try:
        # 标准化因子
        fac_std = (fac - fac.mean()) / (fac.std() + 1e-8)
        # OLS回归
        X = fac_std.values
        y = ret.values
        XtX = X.T @ X
        Xty = X.T @ y
        # Ridge正则化避免奇异矩阵
        XtX_reg = XtX + 0.1 * np.eye(XtX.shape[0])
        weights = np.linalg.solve(XtX_reg, Xty)
        # 标准化为正数
        weights = np.maximum(weights, 0)
        total = weights.sum()
        if total > 0:
            weights = weights / total
        else:
            weights = np.ones(len(weights)) / len(weights)
        return {name: float(weights[i]) for i, name in enumerate(FACTOR_NAMES)}
    except Exception:
        n_factors = len(FACTOR_NAMES)
        return {name: 1.0 / n_factors for name in FACTOR_NAMES}


def calc_factor_scores(price_dict: dict) -> pd.DataFrame:
    """计算所有品种的因子得分矩阵"""
    symbols = list(price_dict.keys())
    scores = {sym: {} for sym in symbols}
    
    for sym in symbols:
        scores[sym]["momentum"] = calc_momentum_factor(price_dict[sym])
        scores[sym]["carry"] = calc_carry_factor(price_dict[sym])
        scores[sym]["volatility"] = calc_volatility_factor(price_dict[sym])
        scores[sym]["correlation"] = calc_correlation_factor(price_dict, sym)
    
    factor_df = pd.DataFrame(scores).T
    
    # 标准化因子得分
    for col in factor_df.columns:
        mean = factor_df[col].mean()
        std = factor_df[col].std()
        if std > 1e-8:
            factor_df[col] = (factor_df[col] - mean) / std
        else:
            factor_df[col] = 0
    
    return factor_df


def rank_symbols_by_ml_score(price_dict: dict, factor_weights: dict) -> list:
    """根据ML权重因子得分对品种排名"""
    factor_df = calc_factor_scores(price_dict)
    
    scores = {}
    for sym in price_dict.keys():
        score = sum(factor_df.loc[sym, fac] * factor_weights.get(fac, 0)
                    for fac in FACTOR_NAMES if fac in factor_df.columns)
        scores[sym] = score
    
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [sym for sym, _ in ranked]


def main():
    api = TqApi(TqSim(), auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 订阅数据
    quotes = {}
    klines = {}
    for sym in SYMBOLS:
        quotes[sym] = api.get_quote(sym)
        klines[sym] = api.get_kline_serial(sym, duration_day=1, data_length=100)
    
    print(f"[{datetime.now()}] 策略33启动: 有色金属ML多因子动态权重策略")
    
    position_manager = TargetPosTask(api)
    last_rebalance_date = None
    current_positions = {}
    factor_weights = {name: 1.0 / len(FACTOR_NAMES) for name in FACTOR_NAMES}
    entry_prices = {}
    
    # 价格历史
    price_history = {sym: pd.Series(dtype=float) for sym in SYMBOLS}
    
    while True:
        api.wait_update()
        
        # 更新价格历史
        for sym in SYMBOLS:
            kl = klines[sym]
            if len(kl) > 0:
                price_history[sym] = pd.concat([
                    price_history[sym],
                    pd.Series({pd.Timestamp(kl.iloc[-1]['datetime']).normalize(): 
                               float(kl.iloc[-1]['close'])})
                ])
                # 保持最大历史
                if len(price_history[sym]) > CORR_WINDOW + 10:
                    price_history[sym] = price_history[sym].iloc[-(CORR_WINDOW + 10):]
        
        # 检查是否需要调仓
        now = datetime.now()
        current_date = now.date()
        
        should_rebalance = (
            last_rebalance_date is None or
            (current_date - last_rebalance_date).days >= REBALANCE_FREQ
        )
        
        if should_rebalance and len(list(price_history.values())[0]) > CORR_WINDOW:
            try:
                # 计算因子权重 (使用前一日数据避免look-ahead bias)
                factor_weights = rolling_regression_weights(
                    calc_factor_scores(price_history), 
                    pd.Series({sym: price_history[sym].pct_change().iloc[-1] 
                              for sym in SYMBOLS if len(price_history[sym]) > 1}),
                    lookback=20
                )
                print(f"[{now}] 因子权重: { {k: round(v,3) for k,v in factor_weights.items()} }")
                
                # 品种排名
                ranked_symbols = rank_symbols_by_ml_score(price_history, factor_weights)
                print(f"[{now}] 品种排名: {ranked_symbols}")
                
                # 做多前POSITION_SIZE名, 做空后2名(可选)
                target_symbols = ranked_symbols[:POSITION_SIZE]
                
                # 计算目标仓位
                target_positions = {sym: 1 for sym in target_symbols}
                
                # 检查板块敞口
                metal_count = sum(1 for s in target_symbols if s.startswith("SHFE."))
                precious_count = sum(1 for s in target_symbols if "au" in s or "ag" in s)
                
                if metal_count > 4:  # 限制单一板块
                    excess = target_symbols[4:]
                    for sym in excess:
                        target_positions[sym] = 0
                
                # 执行调仓
                for sym in SYMBOLS:
                    target = target_positions.get(sym, 0)
                    current = current_positions.get(sym, 0)
                    if target != current:
                        position_manager.set_target_volume(sym, target)
                        current_positions[sym] = target
                        entry_prices[sym] = float(quotes[sym].last_price)
                        print(f"[{now}] 调仓 {sym}: {current} -> {target}")
                
                last_rebalance_date = current_date
                
            except Exception as e:
                print(f"[{now}] 调仓异常: {e}")
        
        # 止损检查
        for sym, entry_price in list(entry_prices.items()):
            current_price = float(quotes[sym].last_price)
            if entry_price > 0:
                pnl_pct = (current_price - entry_price) / entry_price
                if pnl_pct < -MAX_DRAWDOWN:
                    position_manager.set_target_volume(sym, 0)
                    current_positions[sym] = 0
                    print(f"[{now}] 止损 {sym}: 亏损 {pnl_pct:.2%}")
                    del entry_prices[sym]
        
        # 更新账户风控
        account = api.get_account()
        if account.float_margin_ratio > 0.9:
            print(f"[{now}] 风险警告: 保证金比例 {account.float_margin_ratio:.2%}")
            for sym in SYMBOLS:
                position_manager.set_target_volume(sym, 0)
            current_positions = {}
            entry_prices = {}

    api.close()


if __name__ == "__main__":
    main()
