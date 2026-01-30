from abc import ABC, abstractmethod
from typing import Optional
from statistics import mean
from app.core.models import MarketDataSnapshot, StrategySignal, MarketRegime, TradeDirection
from app.scoring.models import ScoreComponent

class ScoringStage(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def weight(self) -> float:
        pass

    @property
    def is_critical(self) -> bool:
        """If True, a score of 0.0 in this stage forces an IGNORE verdict."""
        return False

    @abstractmethod
    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        pass

# 1. Data Sanity (Fundament)
class DataSanityStage(ScoringStage):
    name = "1. Data Sanity"
    weight = 2.0  # Critical

    @property
    def is_critical(self) -> bool:
        return True

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        if not snapshot.candles:
            return ScoreComponent(self.name, 0.0, self.weight, "Brak danych")
        
        count = len(snapshot.candles)
        if count < 50:
            return ScoreComponent(self.name, 2.0, self.weight, f"Mało świec ({count})")
        
        return ScoreComponent(self.name, 10.0, self.weight, "Dane kompletne")

# 2. Risk / Reward Geometry
class RiskRewardStage(ScoringStage):
    name = "2. Risk/Reward"
    weight = 1.8

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        if not signal.stop_loss_price or not signal.take_profit_price:
            return ScoreComponent(self.name, 0.0, self.weight, "Brak SL/TP")
        
        entry = snapshot.candles[-1].close
        risk = abs(entry - signal.stop_loss_price)
        reward = abs(signal.take_profit_price - entry)
        
        if risk == 0:
            return ScoreComponent(self.name, 0.0, self.weight, "Risk=0")
            
        rr = reward / risk
        
        score = 0.0
        reason = ""
        if rr < 1.0: 
            score = 1.0
            reason = f"Słabe RR ({rr:.2f})"
        elif rr < 1.5: 
            score = 4.0
            reason = f"Akceptowalne RR ({rr:.2f})"
        elif rr < 2.0: 
            score = 7.0
            reason = f"Dobre RR ({rr:.2f})"
        elif rr < 3.0: 
            score = 9.0
            reason = f"Bardzo dobre RR ({rr:.2f})"
        else: 
            score = 10.0
            reason = f"Znakomite RR ({rr:.2f})"
        
        return ScoreComponent(self.name, score, self.weight, reason)

# 3. Market Regime
class MarketRegimeStage(ScoringStage):
    name = "3. Market Regime"
    weight = 1.5

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        regime = snapshot.regime
        
        if regime == MarketRegime.TREND:
            return ScoreComponent(self.name, 10.0, self.weight, "Trend (Strong)")
        elif regime == MarketRegime.HIGH_VOLATILITY:
            return ScoreComponent(self.name, 6.0, self.weight, "Wysoka zmienność")
        elif regime == MarketRegime.RANGE:
            return ScoreComponent(self.name, 5.0, self.weight, "Konsolidacja")
        elif regime == MarketRegime.LOW_LIQUIDITY:
            return ScoreComponent(self.name, 2.0, self.weight, "Niska płynność")
        else:
            return ScoreComponent(self.name, 4.0, self.weight, str(regime))

# 11. News Risk (Fundamental)
class NewsRiskStage(ScoringStage):
    name = "11. News Risk"
    weight = 2.0  # Critical
    
    @property
    def is_critical(self) -> bool:
        return True

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        impact = snapshot.news_impact
        time_to = snapshot.time_to_news_min
        
        if not impact or time_to is None:
            return ScoreComponent(self.name, 10.0, self.weight, "Brak danych news")
            
        # User requirement:
        # -10 to -30 points penalty if:
        # High Impact AND T-30 to T+15 min
        
        # time_to is "minutes until event". 
        # T-30 means 30 mins before event (time_to = 30)
        # T+15 means 15 mins after event (time_to = -15)
        # So danger zone is time_to between -15 and 30.
        
        if impact == "High":
            # Check danger zone [-15, 30]
            if -15 <= time_to <= 30:
                # Calculate penalty based on proximity
                # Closer to 0 -> higher penalty (-30 pts -> score -15)
                # Further away -> lower penalty (-10 pts -> score -5)
                
                # Simple logic:
                # If within 15 mins (either side): Max penalty (-30 pts)
                if -15 <= time_to <= 15:
                    return ScoreComponent(self.name, -15.0, self.weight, f"⛔ HIGH IMPACT (T{time_to:+.0f}m) - Handel wstrzymany")
                else:
                    # 15 to 30 mins before
                    return ScoreComponent(self.name, -5.0, self.weight, f"⚠️ HIGH IMPACT (T{time_to:+.0f}m) - Ryzyko")
                    
        elif impact == "Medium":
            # Moderate penalty for Medium impact very close
            if -5 <= time_to <= 15:
                 return ScoreComponent(self.name, 2.0, self.weight, f"Medium Impact (T{time_to:+.0f}m)")
                
        return ScoreComponent(self.name, 10.0, self.weight, "Warunki sprzyjające")

# 4. Trend strukturalny (Higher Timeframe Bias)
class TrendBiasStage(ScoringStage):
    name = "4. HTF Trend"
    weight = 1.2

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        candles = snapshot.candles
        if len(candles) < 200:
             return ScoreComponent(self.name, 5.0, self.weight, "Brak danych do analizy trendu")
        
        closes = [c.close for c in candles]
        sma200 = sum(closes[-200:]) / 200
        sma50 = sum(closes[-50:]) / 50
        current_price = closes[-1]
        
        is_uptrend = sma50 > sma200
        direction = signal.signal_type.value
        
        score = 5.0
        reason = "Neutralny"
        
        if direction == "buy":
            if is_uptrend and current_price > sma200:
                score = 10.0
                reason = "Zgodny z trendem wzrostowym"
            elif not is_uptrend and current_price < sma200:
                score = 2.0
                reason = "Kontra trend spadkowy"
        elif direction == "sell":
            if not is_uptrend and current_price < sma200:
                score = 10.0
                reason = "Zgodny z trendem spadkowym"
            elif is_uptrend and current_price > sma200:
                score = 2.0
                reason = "Kontra trend wzrostowy"
                
        return ScoreComponent(self.name, score, self.weight, reason)

# 5. Momentum
class MomentumStage(ScoringStage):
    name = "5. Momentum"
    weight = 1.2

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        candles = snapshot.candles[-3:]
        if len(candles) < 3:
            return ScoreComponent(self.name, 5.0, self.weight, "Brak danych")
            
        direction = signal.signal_type.value
        bullish_candles = sum(1 for c in candles if c.close > c.open)
        bearish_candles = sum(1 for c in candles if c.close < c.open)
        
        score = 5.0
        reason = "Mieszane momentum"
        
        if direction == "buy":
            if bullish_candles == 3:
                score = 10.0
                reason = "Silne momentum wzrostowe"
            elif bullish_candles == 2:
                score = 8.0
                reason = "Umiarkowane momentum wzrostowe"
            elif bullish_candles == 0:
                score = 2.0
                reason = "Momentum spadkowe (kontra)"
        elif direction == "sell":
            if bearish_candles == 3:
                score = 10.0
                reason = "Silne momentum spadkowe"
            elif bearish_candles == 2:
                score = 8.0
                reason = "Umiarkowane momentum spadkowe"
            elif bearish_candles == 0:
                score = 2.0
                reason = "Momentum wzrostowe (kontra)"
                
        return ScoreComponent(self.name, score, self.weight, reason)

# 6. Overextension / Mean Reversion
class MeanReversionStage(ScoringStage):
    name = "6. Mean Reversion"
    weight = 1.0

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        candles = snapshot.candles
        if len(candles) < 20:
             return ScoreComponent(self.name, 5.0, self.weight, "N/A")
             
        closes = [c.close for c in candles]
        sma20 = sum(closes[-20:]) / 20
        last = closes[-1]
        dist_pct = (last - sma20) / sma20
        
        score = 5.0
        reason = "W normie"
        
        if signal.signal_type.value == "buy":
            if dist_pct < -0.02:
                score = 9.0
                reason = "Cena atrakcyjna (poniżej średniej)"
            elif dist_pct > 0.05:
                score = 3.0
                reason = "Cena 'naciągnięta' (overextended)"
        elif signal.signal_type.value == "sell":
            if dist_pct > 0.02:
                score = 9.0
                reason = "Cena atrakcyjna (powyżej średniej)"
            elif dist_pct < -0.05:
                score = 3.0
                reason = "Cena 'naciągnięta' w dół"
                
        return ScoreComponent(self.name, score, self.weight, reason)

# 7. Volatility Context
class VolatilityContextStage(ScoringStage):
    name = "7. Volatility"
    weight = 1.0

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        candles = snapshot.candles
        if len(candles) < 10:
             return ScoreComponent(self.name, 5.0, self.weight, "N/A")
             
        ranges = [c.high - c.low for c in candles[-10:]]
        avg_range = sum(ranges) / len(ranges)
        last_range = ranges[-1]
        
        ratio = last_range / avg_range if avg_range > 0 else 1.0
        
        score = 5.0
        reason = "OK"
        if 0.8 <= ratio <= 1.5:
            score = 10.0
            reason = "Zmienność w normie"
        elif ratio > 2.0:
            score = 4.0
            reason = "Ekstremalna zmienność (ryzyko)"
        elif ratio < 0.5:
            score = 6.0
            reason = "Bardzo mała zmienność (cisza)"
            
        return ScoreComponent(self.name, score, self.weight, reason)

# 8. Confluence
class ConfluenceStage(ScoringStage):
    name = "8. Confluence"
    weight = 0.8

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        # Sprawdzamy bliskość "okrągłych liczb" (Psychological Levels)
        # Np. 1.1000, 150.00, 20000
        current_price = snapshot.candles[-1].close
        
        # Logika dla różnych skal cenowych (Forex vs Crypto vs Stocks)
        import math
        if current_price < 10:
            step = 0.5
        elif current_price < 1000:
            step = 10.0
        else:
            step = 100.0
            
        nearest_level = round(current_price / step) * step
        distance_pct = abs(current_price - nearest_level) / current_price
        
        score = 5.0
        reason = "Brak confluence"
        
        # Jeśli jesteśmy bardzo blisko (< 0.2%) ważnego poziomu
        if distance_pct < 0.002:
            score = 8.0
            reason = f"Blisko poziomu {nearest_level}"
            
        return ScoreComponent(self.name, score, self.weight, reason)

# 9. Expectancy
class ExpectancyStage(ScoringStage):
    name = "9. Expectancy"
    weight = 0.8

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        return ScoreComponent(self.name, 5.0, self.weight, "Brak danych historycznych")

# 10. Timing
class TimingStage(ScoringStage):
    name = "10. Timing"
    weight = 0.5

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> ScoreComponent:
        # Piątkowy filtr ("Friday Doom")
        # Unikamy otwierania pozycji w piątek po 16:00 (ryzyko weekendowe)
        last_candle_time = snapshot.candles[-1].time
        weekday = last_candle_time.weekday() # 0=Mon, 4=Fri
        hour = last_candle_time.hour
        
        if weekday == 4 and hour >= 16:
            return ScoreComponent(self.name, 2.0, self.weight, "Piątek po południu (ryzyko!)")
        
        if weekday == 0 and hour < 8:
             return ScoreComponent(self.name, 4.0, self.weight, "Poniedziałek rano (luki)")

        return ScoreComponent(self.name, 8.0, self.weight, "Czas OK")

