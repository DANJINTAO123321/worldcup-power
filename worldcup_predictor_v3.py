#!/usr/bin/env python3
"""
世界杯预测 - 动态多因子量化模型 v3.0
======================================
【胜负平 + 比分预测双轨模式】

核心升级：
  1. 胜负平预测（保留 v2 核心逻辑）
  2. 比分预测：基于多因子 xG 期望，用泊松分布模拟进球概率
  3. 双保险比分推荐：首选（顺应大盘）+ 次选（爆冷对冲）

数据源: football-data.co.uk (开源免凭证 CSV)
Author: 新加坡小龙虾 (shrimp_1)
Date: 2026-06-21 v3.0
"""

import requests
import pandas as pd
import numpy as np
from io import StringIO
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from scipy.stats import poisson
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 第一模块：真实赔率数据抓取
# ============================================================

LEAGUE_CODES = {
    'E0': 'Premier League', 'D1': 'Bundesliga',
    'SP1': 'La Liga', 'I1': 'Serie A', 'F1': 'Ligue 1',
    'N1': 'Eredivisie', 'B1': 'Jupiler Pro League',
    'P1': 'Primeira Liga', 'T1': 'Süper Lig',
}

CSV_BASE = 'https://www.football-data.co.uk/mmz4281'
CURRENT_SEASON = '2526'


class RealOddsFetcher:
    """从 football-data.co.uk 抓取真实赔率 CSV"""

    def __init__(self, cache_dir: str = '/tmp/football_data'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WorldCupPredictor/3.0',
            'Accept': 'text/csv,application/xhtml+xml',
        })
        self._cache: Dict[str, pd.DataFrame] = {}

    def _season_url(self, league: str) -> str:
        return f'{CSV_BASE}/{CURRENT_SEASON}/{league}.csv'

    def download(self, league: str, force: bool = False) -> Optional[pd.DataFrame]:
        cache = self.cache_dir / f'{league}_{CURRENT_SEASON}.csv'
        if not force and cache.exists():
            age = datetime.now() - datetime.fromtimestamp(cache.stat().st_mtime)
            if age < timedelta(hours=6):
                df = pd.read_csv(cache)
                self._cache[league] = df
                return df
        url = self._season_url(league)
        try:
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
            cache.write_bytes(r.content)
            df = pd.read_csv(StringIO(r.text))
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            self._cache[league] = df
            print(f'  [CSV] {league}: {len(df)} 场, 最新 {df["Date"].max()}')
            return df
        except Exception as e:
            print(f'  [CSV] {league} 失败: {e}')
            if cache.exists():
                try:
                    df = pd.read_csv(cache)
                    self._cache[league] = df
                    return df
                except:
                    pass
            return None

    def download_all(self, leagues: List[str] = None) -> Dict[str, pd.DataFrame]:
        if leagues is None:
            leagues = list(LEAGUE_CODES.keys())
        results = {}
        for code in leagues:
            df = self.download(code)
            if df is not None and len(df) > 0:
                results[code] = df
        return results

    def find_match(self, team_a: str, team_b: str, league: str = 'E0') -> Optional[pd.Series]:
        df = self._cache.get(league)
        if df is None:
            df = self.download(league)
        if df is None:
            return None

        mask_ah = (
            df['HomeTeam'].str.contains(team_a, case=False, na=False) &
            df['AwayTeam'].str.contains(team_b, case=False, na=False)
        )
        mask_bh = (
            df['HomeTeam'].str.contains(team_b, case=False, na=False) &
            df['AwayTeam'].str.contains(team_a, case=False, na=False)
        )
        matches = df[mask_ah | mask_bh].sort_values('Date', ascending=False)
        if len(matches) == 0:
            return None

        row = matches.iloc[0]
        if team_a.lower() in str(row['HomeTeam']).lower():
            return row
        else:
            swapped = row.copy()
            swapped['HomeTeam'], swapped['AwayTeam'] = row['AwayTeam'], row['HomeTeam']
            for col in df.columns:
                if col.endswith('H') and col[:-1] + 'A' in df.columns:
                    swapped[col], swapped[col[:-1] + 'A'] = row[col[:-1] + 'A'], row[col]
            if 'FTHG' in df.columns and 'FTAG' in df.columns:
                swapped['FTHG'], swapped['FTAG'] = row['FTAG'], row['FTHG']
                if 'HTHG' in df.columns:
                    swapped['HTHG'], swapped['HTAG'] = row['HTAG'], row['HTHG']
                if 'HTR' in df.columns:
                    htr_map = {'H': 'A', 'A': 'H', 'D': 'D'}
                    swapped['HTR'] = htr_map.get(row['HTR'], row['HTR'])
            ftr_map = {'H': 'A', 'A': 'H', 'D': 'D'}
            swapped['FTR'] = ftr_map.get(row['FTR'], row['FTR'])
            return swapped


# ============================================================
# 第二模块：赔率先验处理
# ============================================================

class OddsPriorModule:
    def __init__(self, odds_home: float, odds_draw: float, odds_away: float):
        self.raw = (odds_home, odds_draw, odds_away)
        self._prior = self._compute()

    def _compute(self) -> Dict[str, float]:
        p_h, p_d, p_a = 1 / self.raw[0], 1 / self.raw[1], 1 / self.raw[2]
        margin = (p_h + p_d + p_a) - 1.0
        draw_m = margin * 0.4
        other_m = (margin - draw_m) / 2
        fair_h = max(0.01, p_h - other_m)
        fair_d = max(0.01, p_d - draw_m)
        fair_a = max(0.01, p_a - other_m)
        tot = fair_h + fair_d + fair_a
        return {'win': fair_h / tot, 'draw': fair_d / tot, 'lose': fair_a / tot}

    def get_prior(self) -> Dict[str, float]:
        return self._prior

    def apply_adjustment(self, raw_prob: Dict[str, float], max_shift: float = 0.15) -> Dict[str, float]:
        final = {}
        for k in ['win', 'draw', 'lose']:
            shift = raw_prob[k] - self._prior[k]
            shift = max(-max_shift, min(max_shift, shift))
            final[k] = self._prior[k] + shift
        tot = sum(final.values())
        return {k: v / tot for k, v in final.items()}


# ============================================================
# 第三模块：球队特征向量
# ============================================================

@dataclass
class TeamFeatures:
    team_name: str
    fifa_rank: int
    power_score: float
    avg_xg: float
    avg_xga: float
    xg_trend: List[float]
    xga_trend: List[float]
    group_points: int
    group_goal_diff: int
    must_win: bool
    draw_ok: bool
    injury_penalty: float
    key_missing: str


# ============================================================
# 第四模块：比分预测引擎 v3.0
# ============================================================

class ScorePredictor:
    """
    比分预测核心算法 v3.0

    基于多因子 xG 期望 + 泊松分布模拟：
      1. 计算双方预期进球 xG_home, xG_away
      2. 用泊松分布生成进球概率矩阵
      3. 结合胜负平概率进行校准
      4. 输出双保险比分推荐
    """

    MAX_GOALS = 6  # 比分概率表最大进球数

    def __init__(self, xg_weight: float = 0.30,
                 mot_weight: float = 0.20,
                 inj_weight: float = 0.10,
                 pwr_weight: float = 0.40,
                 upset_threshold: float = 0.10):
        self.XG_WEIGHT = xg_weight
        self.MOT_WEIGHT = mot_weight
        self.INJ_WEIGHT = inj_weight
        self.PWR_WEIGHT = pwr_weight
        self.UPSET_THRESHOLD = upset_threshold

    # ========== xG 因子 ==========
    def _xg_factor(self, team: TeamFeatures) -> float:
        if len(team.xg_trend) < 3:
            net = team.avg_xg - team.avg_xga
        else:
            w = [0.4, 0.25, 0.15, 0.1, 0.1]
            xg_w = sum(ww * x for ww, x in zip(w, team.xg_trend))
            xga_w = sum(ww * x for ww, x in zip(w, team.xga_trend))
            net = xg_w - xga_w
        return max(-1.0, min(1.0, net / 1.5))

    # ========== 战意因子 ==========
    def _mot_factor(self, team: TeamFeatures) -> float:
        if team.group_points >= 6:
            return 0.25
        if team.group_points == 0:
            return 0.20
        if team.must_win:
            return 1.0 if team.group_goal_diff < 0 else 0.85
        if team.draw_ok:
            return 0.55
        return 0.65

    # ========== 伤病因子 ==========
    def _inj_factor(self, team: TeamFeatures) -> float:
        return -team.injury_penalty * 0.5 if team.key_missing else 0.0

    # ========== 计算预期进球数 ==========
    def _calc_expected_goals(self, team: TeamFeatures, is_home: bool) -> float:
        """
        计算球队预期进球数：
          - 基础：avg_xg（主场加成 +0.3，客场 -0.1）
          - 因子调整：战意、伤病、武力值
        """
        base = team.avg_xg if is_home else max(0.5, team.avg_xg - 0.4)
        if is_home:
            base += 0.25  # 主场优势

        xg_f = self._xg_factor(team)
        mot_f = self._mot_factor(team)
        inj_f = self._inj_factor(team)

        modifier = (
            xg_f * self.XG_WEIGHT +
            mot_f * self.MOT_WEIGHT +
            inj_f * self.INJ_WEIGHT +
            (team.power_score / 100) * self.PWR_WEIGHT * 0.3
        )
        expected = base * (1 + modifier * 0.4)
        return max(0.2, min(4.0, expected))

    # ========== 泊松概率矩阵 ==========
    def _poisson_matrix(self, lam: float) -> np.ndarray:
        """生成泊松分布进球概率（0-MAX_GOALS球）"""
        probs = [poisson.pmf(k, lam) for k in range(self.MAX_GOALS + 1)]
        # 0-6球概率和归一化
        total = sum(probs)
        return [p / total for p in probs]

    # ========== 比分概率矩阵 ==========
    def _score_prob_matrix(self,
                           team_a: TeamFeatures,
                           team_b: TeamFeatures,
                           final_prob: Dict[str, float],
                           is_home_a: bool = True) -> Dict[str, float]:
        """
        生成比分概率矩阵，结合泊松分布和胜负平概率校准
        """
        # 预期进球
        exp_a = self._calc_expected_goals(team_a, is_home=is_home_a)
        exp_b = self._calc_expected_goals(team_b, is_home=not is_home_a)

        # 泊松概率
        prob_a = self._poisson_matrix(exp_a)  # 主队进球概率[0-6+]
        prob_b = self._poisson_matrix(exp_b)  # 客队进球概率

        # 生成比分概率矩阵
        score_probs = {}
        for ga in range(self.MAX_GOALS + 1):
            for gb in range(self.MAX_GOALS + 1):
                if ga == self.MAX_GOALS and gb < 3:
                    continue  # 跳过不太可能的极端
                if gb == self.MAX_GOALS and ga < 3:
                    continue

                raw_p = prob_a[ga] * prob_b[gb]

                # 判断胜负平方向并校准
                if ga > gb:
                    direction = 'win'
                elif ga == gb:
                    direction = 'draw'
                else:
                    direction = 'lose'

                # 用胜负平概率校准
                calibrated_p = raw_p * (1 + (final_prob[direction] - 1/3) * 2)
                score_probs[f'{ga}-{gb}'] = max(0.0001, calibrated_p)

        # 归一化
        total = sum(score_probs.values())
        return {k: v / total for k, v in score_probs.items()}

    # ========== 双保险比分推荐 ==========
    def predict_score(self,
                      team_a: TeamFeatures,
                      team_b: TeamFeatures,
                      final_prob: Dict[str, float],
                      prior_prob: Dict[str, float]) -> Dict:
        """
        完整比分预测：
          - 首选比分（顺应大盘）
          - 次选比分（爆冷对冲）
          - 比分概率分布表
        """
        # 比分概率矩阵
        score_probs = self._score_prob_matrix(team_a, team_b, final_prob)

        # 按概率排序
        sorted_scores = sorted(score_probs.items(), key=lambda x: -x[1])

        # 判断强弱
        weak_team = team_b if team_b.fifa_rank > team_a.fifa_rank else team_a
        weak_is_b = (weak_team == team_b)

        # 首选比分：概率最高的
        primary = sorted_scores[0][0]

        # 次选比分策略
        # 1. 如果弱队被严重低估（upset），选弱队方向
        # 2. 否则选次高概率
        upset_triggered = False
        if weak_is_b:
            uplift = final_prob['lose'] - prior_prob['lose']
            upset_triggered = uplift >= self.UPSET_THRESHOLD
        else:
            uplift = final_prob['win'] - prior_prob['win']
            upset_triggered = uplift >= self.UPSET_THRESHOLD

        if upset_triggered:
            # 爆冷方向：找弱队可能的比分
            if weak_is_b:
                # 弱队是B（客队），找客队进球多或平局的比分
                candidates = [(s, p) for s, p in sorted_scores
                              if int(s.split('-')[1]) >= int(s.split('-')[0])]
            else:
                # 弱队是A（主队），找主队进球多的比分
                candidates = [(s, p) for s, p in sorted_scores
                              if int(s.split('-')[0]) >= int(s.split('-')[1])]
            secondary = candidates[1][0] if len(candidates) > 1 else sorted_scores[1][0]
        else:
            # 正常：选次高概率
            secondary = sorted_scores[1][0]

        # 生成概率分布表（TOP 10）
        top_scores = sorted_scores[:10]

        # 总进球数预测
        total_goals_probs = self._calc_total_goals(score_probs)

        # 双方都进球概率
        bts_prob = sum(p for s, p in score_probs.items()
                       if int(s.split('-')[0]) > 0 and int(s.split('-')[1]) > 0)

        return {
            'primary_score': primary,
            'primary_prob': score_probs[primary],
            'secondary_score': secondary,
            'secondary_prob': score_probs[secondary],
            'upset_warning': upset_triggered,
            'upset_uplift': uplift if upset_triggered else 0,
            'top_scores': top_scores,
            'total_goals_prob': total_goals_probs,
            'bts_prob': bts_prob,
            'expected_home_goals': round(
                sum(int(s.split('-')[0]) * p for s, p in score_probs.items()), 2),
            'expected_away_goals': round(
                sum(int(s.split('-')[1]) * p for s, p in score_probs.items()), 2),
        }

    def _calc_total_goals(self, score_probs: Dict[str, float]) -> Dict[str, float]:
        """计算总进球数概率分布"""
        totals = {'0-1': 0, '2-3': 0, '4+': 0}
        for s, p in score_probs.items():
            g = int(s.split('-')[0]) + int(s.split('-')[1])
            if g <= 1:
                totals['0-1'] += p
            elif g <= 3:
                totals['2-3'] += p
            else:
                totals['4+'] += p
        return totals


# ============================================================
# 第五模块：多因子量化模型 v3（整合比分预测）
# ============================================================

class MultiFactorModel:
    """
    动态多因子量化模型 v3.0

    模式判断：
      排名差 ≥ 20 → 基础武力差模式
      排名差 < 20 → 多因子 + 赔率先验贝叶斯融合

    新增：爆冷预警 + 比分预测双轨输出
    """

    XG_WEIGHT = 0.30
    MOT_WEIGHT = 0.20
    INJ_WEIGHT = 0.10
    PWR_WEIGHT = 0.40
    MAX_SHIFT = 0.15
    UPSET_THRESHOLD = 0.10

    def __init__(self):
        self.score_predictor = ScorePredictor(
            xg_weight=self.XG_WEIGHT,
            mot_weight=self.MOT_WEIGHT,
            inj_weight=self.INJ_WEIGHT,
            pwr_weight=self.PWR_WEIGHT,
            upset_threshold=self.UPSET_THRESHOLD
        )

    def _xg_factor(self, team: TeamFeatures) -> float:
        if len(team.xg_trend) < 3:
            net = team.avg_xg - team.avg_xga
        else:
            w = [0.4, 0.25, 0.15, 0.1, 0.1]
            xg_w = sum(ww * x for ww, x in zip(w, team.xg_trend))
            xga_w = sum(ww * x for ww, x in zip(w, team.xga_trend))
            net = xg_w - xga_w
        return max(-1.0, min(1.0, net / 1.5))

    def _mot_factor(self, team: TeamFeatures) -> float:
        if team.group_points >= 6:
            return 0.25
        if team.group_points == 0:
            return 0.20
        if team.must_win:
            return 1.0 if team.group_goal_diff < 0 else 0.85
        if team.draw_ok:
            return 0.55
        return 0.65

    def _inj_factor(self, team: TeamFeatures) -> float:
        return -team.injury_penalty * 0.5 if team.key_missing else 0.0

    def _raw_score(self, team: TeamFeatures) -> float:
        power = team.power_score / 100.0
        xg = self._xg_factor(team)
        mot = self._mot_factor(team)
        inj = self._inj_factor(team)
        return (
            power * self.PWR_WEIGHT +
            (xg + 1) / 2 * self.XG_WEIGHT +
            mot * self.MOT_WEIGHT +
            (1 + inj) * self.INJ_WEIGHT
        )

    def _raw_to_probs(self, sa: float, sb: float) -> Dict[str, float]:
        ea = np.exp(sa * 3)
        eb = np.exp(sb * 3)
        ed = np.exp((min(sa, sb) - 0.1) * 3)
        t = ea + ed + eb
        return {'win': ea / t, 'draw': ed / t, 'lose': eb / t}

    def predict(self,
                team_a: TeamFeatures,
                team_b: TeamFeatures,
                odds_home: float = 2.1,
                odds_draw: float = 3.2,
                odds_away: float = 3.5,
                rank_diff: int = None) -> Dict:
        if rank_diff is None:
            rank_diff = abs(team_a.fifa_rank - team_b.fifa_rank)

        odds_mod = OddsPriorModule(odds_home, odds_draw, odds_away)
        prior = odds_mod.get_prior()

        sa = self._raw_score(team_a)
        sb = self._raw_score(team_b)
        raw = self._raw_to_probs(sa, sb)
        final = odds_mod.apply_adjustment(raw, max_shift=self.MAX_SHIFT)

        # 爆冷检测
        weak_team = team_b if team_b.fifa_rank > team_a.fifa_rank else team_a
        weak_key = 'lose' if weak_team == team_b else 'win'
        uplift = final[weak_key] - prior[weak_key]
        upset_triggered = uplift >= self.UPSET_THRESHOLD

        upset_msg = ""
        if upset_triggered:
            strong_key = 'win' if weak_key == 'lose' else 'lose'
            strong_team = team_a if weak_key == 'lose' else team_b
            upset_msg = (
                f"⚠️ 【爆冷风控预警】\n"
                f"   {weak_team.team_name} 多因子概率({final[weak_key]:.1%}) "
                f"比市场先验({prior[weak_key]:.1%})高出 {uplift:.1%}（阈值10%）\n"
                f"   → {strong_team.team_name} 存在极高翻车风险！\n"
                f"   → 推荐防冷：平局 / {weak_team.team_name} 不败！"
            )

        # 大胜补偿检测
        power_diff = team_a.power_score - team_b.power_score
        score_diff = sa - sb
        big_win_triggered = False
        big_win_msg = ""
        if upset_triggered and power_diff >= 25 and score_diff > 0.3:
            big_win_triggered = True
            big_win_msg = (
                f"🔥 【大胜补偿预警】（v2.1机制）\n"
                f"   {team_a.team_name} 武力值依然碾压（武力差={power_diff:.0f}）\n"
                f"   → 强队存在【突然暴走】打穿零封的可能性！\n"
                f"   → 次选须保留：{team_a.team_name} 3:0 / 4:0 零封大胜！"
            )

        # 比分预测
        score_result = self.score_predictor.predict_score(
            team_a, team_b, final, prior
        )

        best = max(final, key=final.get)
        confidence = abs(final[best] - 1 / 3) * 3

        result = {
            'team_a': team_a.team_name,
            'team_b': team_b.team_name,
            'rank_diff': rank_diff,
            'mode': 'multi_factor_odds' if rank_diff < 20 else 'rank_based',
            'prior_market': prior,
            'raw_prob': raw,
            'final_prob': final,
            'prediction': best.upper(),
            'confidence': round(confidence, 2),
            'upset_warning': upset_triggered,
            'upset_msg': upset_msg,
            'big_win_compensation': big_win_triggered,
            'big_win_msg': big_win_msg,
            'score_a': round(sa, 3),
            'score_b': round(sb, 3),
            'odds_raw': {'home': odds_home, 'draw': odds_draw, 'away': odds_away},
            # 比分预测结果
            'score_prediction': score_result,
        }
        return result


# ============================================================
# 第六模块：球队特征估算
# ============================================================

RANK_POWER_MAP = {
    1: 95, 2: 93, 3: 91, 4: 90, 5: 88,
    6: 87, 7: 86, 8: 85, 9: 83, 10: 82,
    11: 80, 12: 79, 13: 78, 14: 76, 15: 75,
    16: 73, 17: 71, 18: 70, 19: 68, 20: 66,
    21: 64, 22: 62, 23: 60, 24: 58, 25: 56,
    26: 54, 27: 52, 28: 50, 29: 48, 30: 46,
}


def estimate_team_features(team_name: str,
                            fifa_rank: int = None,
                            group_points: int = 0,
                            group_goal_diff: int = 0,
                            must_win: bool = False,
                            draw_ok: bool = True,
                            injury_penalty: float = 0.0,
                            key_missing: str = "") -> TeamFeatures:
    if fifa_rank is None:
        rank = _guess_rank(team_name)
    else:
        rank = fifa_rank

    power = RANK_POWER_MAP.get(rank, max(50, 80 - rank * 0.5))

    np.random.seed(hash(team_name) % 2 ** 32)
    base_xg = max(0.6, 2.8 - rank * 0.065 + np.random.uniform(-0.15, 0.15))
    base_xga = max(0.4, 2.5 - power / 100 * 1.5 + np.random.uniform(-0.15, 0.15))

    xg_t = [max(0.1, base_xg + np.random.randn() * 0.5) for _ in range(5)]
    xga_t = [max(0.1, base_xga + np.random.randn() * 0.5) for _ in range(5)]

    return TeamFeatures(
        team_name=team_name,
        fifa_rank=rank,
        power_score=power,
        avg_xg=round(np.mean(xg_t), 2),
        avg_xga=round(np.mean(xga_t), 2),
        xg_trend=[round(x, 2) for x in xg_t],
        xga_trend=[round(x, 2) for x in xga_t],
        group_points=group_points,
        group_goal_diff=group_goal_diff,
        must_win=must_win,
        draw_ok=draw_ok,
        injury_penalty=injury_penalty,
        key_missing=key_missing,
    )


def _guess_rank(team_name: str) -> int:
    known = {
        'Man City': 1, 'Man United': 13, 'Arsenal': 3,
        'Liverpool': 7, 'Chelsea': 14, 'Tottenham': 11,
        'Aston Villa': 9, 'Newcastle': 10, 'Brighton': 12,
        'West Ham': 17, 'Crystal Palace': 19, 'Fulham': 20,
        'Brentford': 16, 'Everton': 18, 'Leeds': 22,
        'Burnley': 21, 'Wolves': 15, 'Leicester': 25,
        'Dortmund': 8, 'Bayern': 5, 'Real Madrid': 2,
        'Barcelona': 4, 'Atletico': 6, 'Villarreal': 15,
        'Ath Madrid': 6, 'Roma': 18, 'Milan': 12,
        'Inter': 10, 'Juventus': 14, 'Monaco': 17,
        'PSG': 3, 'Leverkusen': 11, 'Frankfurt': 20,
    }
    for key, r in known.items():
        if key.lower() in team_name.lower():
            return r
    return 15


# ============================================================
# 第七模块：结果打印（比分版）
# ============================================================

def print_result_v3(result: Dict, actual_ftr: str = None,
                    actual_score: str = None):
    """格式化打印预测结果 v3.0（比分版）"""

    print()
    print("=" * 70)
    print(f"🏟️  {result['team_a']} vs {result['team_b']}")
    print(f"📊 排名差: {result['rank_diff']} | 模式: {result['mode']}")
    print("=" * 70)

    # 赔率信息
    o = result['odds_raw']
    p = result['prior_market']
    print(f"\n📈 市场赔率 → 去抽水先验:")
    print(f"   原始赔率: {result['team_a']}胜={o['home']} | 平={o['draw']} | {result['team_b']}胜={o['away']}")
    print(f"   去抽水后: {result['team_a']} {p['win']:>5.1%} | {p['draw']:>5.1%} | {p['lose']:>5.1%} {result['team_b']}")

    print(f"\n🧠 多因子Raw: {result['team_a']} {result['raw_prob']['win']:>5.1%} | {result['raw_prob']['draw']:>5.1%} | {result['raw_prob']['lose']:>5.1%} {result['team_b']}")

    fp = result['final_prob']
    print(f"\n🎯 最终概率（赔率先验±15%融合）:")
    print(f"   ┌──────────────┬──────────┐")
    print(f"   │ {result['team_a']} 胜    │ {fp['win']:>6.1%}  │")
    print(f"   │ 平局         │ {fp['draw']:>6.1%}  │")
    print(f"   │ {result['team_b']} 胜    │ {fp['lose']:>6.1%}  │")
    print(f"   └──────────────┴──────────┘")

    print(f"\n🔮 押注方向: 【{result['prediction']}】")
    print(f"   信心度: {result['confidence']:.0%} ({'高' if result['confidence']>0.6 else '中' if result['confidence']>0.4 else '低'})")

    # ========== 比分预测核心输出 ==========
    sr = result['score_prediction']
    print(f"\n🏆 【比分预测】")
    print(f"   ┌─────────────────────────────────────────────┐")
    print(f"   │ 🏆 首选比分: {result['team_a']} {sr['primary_score']} {result['team_b']}   (概率: {sr['primary_prob']:.1%}) │")
    print(f"   │ 🛡️ 次选比分: {result['team_a']} {sr['secondary_score']} {result['team_b']}   (概率: {sr['secondary_prob']:.1%}) │")
    print(f"   └─────────────────────────────────────────────┘")

    # 比分概率分布
    print(f"\n📋 比分概率分布 TOP10:")
    print(f"   排名  比分   概率    累计")
    cumulative = 0
    for i, (score, prob) in enumerate(sr['top_scores']):
        cumulative += prob
        bar = '█' * int(prob * 100)
        print(f"   {i+1:2d}.  {score}  {prob:>5.1%}  {cumulative:>5.1%}  {bar}")
        if i >= 9:
            break

    # 总进球数
    tg = sr['total_goals_prob']
    print(f"\n📊 总进球数:")
    print(f"   0-1球: {tg['0-1']:.1%}  |  2-3球: {tg['2-3']:.1%}  |  4+球: {tg['4+']:.1%}")

    # 双方都进球
    print(f"   双方都进球(BTS): {sr['bts_prob']:.1%}")

    # 预期进球
    print(f"   预期进球: {result['team_a']} {sr['expected_home_goals']:.1f} - {sr['expected_away_goals']:.1f} {result['team_b']}")

    # 爆冷预警
    if result['upset_warning']:
        print()
        print("━" * 70)
        print(result['upset_msg'])
        print("━" * 70)

    if result.get('big_win_compensation'):
        print()
        print("━" * 70)
        print(result['big_win_msg'])
        print("━" * 70)

    # 实际结果验证
    if actual_ftr:
        actual_map = {'H': 'win', 'D': 'draw', 'A': 'lose'}
        actual_key = actual_map.get(actual_ftr, 'unknown')
        wdl_hit = fp[actual_key] == max(fp.values())
        print(f"\n📌 实际结果: {actual_ftr} ({actual_score or '?'})")
        print(f"   胜负平预测: {'✅ 命中!' if wdl_hit else '❌ 未命中'}")

        if actual_score:
            # 检查比分命中
            ga, gb = actual_score.split('-')
            primary = sr['primary_score']
            secondary = sr['secondary_score']
            primary_hit = (f'{ga}-{gb}' == primary)
            secondary_hit = (f'{ga}-{gb}' == secondary)
            print(f"   首选比分: {primary} → {'✅ 精准命中!' if primary_hit else '❌ 未命中'}")
            print(f"   次选比分: {secondary} → {'✅ 精准命中!' if secondary_hit else '❌ 未命中'}")
            if not primary_hit and not secondary_hit:
                print(f"   实际比分: {actual_score}")

    print("=" * 70)


# ============================================================
# 主程序入口
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("🌐 世界杯预测系统 v3.0 - 比分预测版")
    print("=" * 70)

    fetcher = RealOddsFetcher()
    fetcher.download_all(['E0', 'D1', 'SP1', 'I1', 'F1'])

    model = MultiFactorModel()

    # ── 示例比赛1: Man City vs Aston Villa ──
    print("\n" + "▶" * 35)
    print("📋 比赛1: Man City vs Aston Villa")
    print("▶" * 35)

    match1 = fetcher.find_match('Man City', 'Aston Villa')
    if match1 is not None:
        odds1 = (float(match1['B365H']), float(match1['B365D']), float(match1['B365A']))
        team_city = estimate_team_features('Man City', fifa_rank=1)
        team_villa = estimate_team_features('Aston Villa', fifa_rank=9)
        r1 = model.predict(team_city, team_villa, *odds1)
        print_result_v3(r1, actual_ftr=match1['FTR'],
                        actual_score=f"{match1['FTHG']}-{match1['FTAG']}")

    # ── 示例比赛2: Crystal Palace vs Arsenal ──
    print("\n" + "▶" * 35)
    print("📋 比赛2: Crystal Palace vs Arsenal")
    print("▶" * 35)

    match2 = fetcher.find_match('Crystal Palace', 'Arsenal')
    if match2 is not None:
        odds2 = (float(match2['B365H']), float(match2['B365D']), float(match2['B365A']))
        team_cp = estimate_team_features('Crystal Palace', fifa_rank=19)
        team_ars = estimate_team_features('Arsenal', fifa_rank=3)
        r2 = model.predict(team_cp, team_ars, *odds2)
        print_result_v3(r2, actual_ftr=match2['FTR'],
                        actual_score=f"{match2['FTHG']}-{match2['FTAG']}")

    print("\n✅ worldcup_predictor_v3.py v3.0 - 比分预测版 完成!")