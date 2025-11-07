"""
Project Xylen - Risk Manager
Python 3.10.12 compatible
Implements position sizing, risk limits, circuit breakers, and trade validation
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math

logger = logging.getLogger(__name__)


class PositionSizeMethod(Enum):
    """Position sizing methods"""
    FIXED_FRACTION = "fixed_fraction"
    KELLY = "kelly"
    FIXED_AMOUNT = "fixed_amount"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Trading halted
    COOLDOWN = "cooldown"  # Waiting to reset


@dataclass
class Trade:
    """Trade record for performance tracking"""
    timestamp: float
    symbol: str
    side: str  # 'BUY' or 'SELL'
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float = 0.0
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    closed: bool = False
    
    
@dataclass
class RiskMetrics:
    """Current risk metrics"""
    total_equity: float
    available_margin: float
    total_exposure: float
    open_positions: int
    daily_pnl: float
    daily_trades: int
    consecutive_losses: int
    win_rate: float
    sharpe_ratio: Optional[float] = None


@dataclass
class PositionSize:
    """Calculated position size"""
    quantity: float
    size_usd: float
    leverage: float
    method: str
    risk_percent: float
    kelly_fraction: Optional[float] = None


class RiskManager:
    """
    Production-grade risk manager with:
    - Multiple position sizing methods (fixed fraction, Kelly criterion)
    - Hard position and exposure limits
    - Circuit breakers for consecutive losses
    - Daily loss limits
    - Emergency shutdown logic
    - Margin requirement validation
    """
    
    def __init__(self, config: Dict):
        """
        Initialize risk manager with configuration
        
        Args:
            config: Configuration dictionary with trading and safety parameters
        """
        self.config = config
        self.trading_config = config.get('trading', {})
        self.safety_config = config.get('safety', {})
        
        # Position sizing parameters
        self.position_size_method = PositionSizeMethod(
            self.trading_config.get('position_size_method', 'fixed_fraction')
        )
        self.position_size_fraction = self.trading_config.get('position_size_fraction', 0.10)
        self.kelly_fraction = self.trading_config.get('kelly_fraction', 0.25)
        self.max_position_size_usd = self.trading_config.get('max_position_size_usd', 1000.0)
        self.min_position_size_usd = self.trading_config.get('min_position_size_usd', 10.0)
        
        # Risk parameters
        self.stop_loss_percent = self.trading_config.get('stop_loss_percent', 0.02)
        self.take_profit_percent = self.trading_config.get('take_profit_percent', 0.05)
        self.max_leverage = self.safety_config.get('max_leverage_allowed', 5)
        
        # Position limits
        self.max_open_positions = self.trading_config.get('max_open_positions', 1)
        self.max_daily_trades = self.trading_config.get('max_daily_trades', 20)
        self.min_trade_interval = self.trading_config.get('min_trade_interval_seconds', 300)
        
        # Safety limits
        self.max_daily_loss_percent = self.safety_config.get('max_daily_loss_percent', 0.10)
        self.max_daily_loss_usd = self.safety_config.get('max_daily_loss_usd', 500.0)
        self.emergency_shutdown_loss_percent = self.safety_config.get(
            'emergency_shutdown_loss_percent', 0.20
        )
        self.max_total_exposure_usd = self.safety_config.get('max_total_exposure_usd', 5000.0)
        
        # Circuit breaker
        self.circuit_breaker_consecutive_losses = self.safety_config.get(
            'circuit_breaker_consecutive_losses', 5
        )
        self.circuit_breaker_cooldown = self.safety_config.get(
            'circuit_breaker_cooldown_seconds', 3600
        )
        self.circuit_breaker_reset_on_win = self.safety_config.get(
            'circuit_breaker_reset_on_win', True
        )
        
        # State tracking
        self.trades: List[Trade] = []
        self.consecutive_losses = 0
        self.circuit_breaker_state = CircuitBreakerState.CLOSED
        self.circuit_breaker_open_time: Optional[float] = None
        self.last_trade_time: Optional[float] = None
        self.daily_reset_time = time.time()
        self.daily_pnl = 0.0
        self.daily_trade_count = 0
        self.emergency_shutdown = False
        self.initial_equity: Optional[float] = None
        
        logger.info(f"RiskManager initialized: method={self.position_size_method.value}, "
                   f"max_daily_loss={self.max_daily_loss_percent*100:.1f}%")
    
    def calculate_position_size(
        self,
        current_price: float,
        account_balance: float,
        leverage: int = 1,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None
    ) -> PositionSize:
        """
        Calculate position size based on configured method
        
        Args:
            current_price: Current market price
            account_balance: Available account balance (equity)
            leverage: Trading leverage (1-125)
            win_rate: Historical win rate (for Kelly)
            avg_win: Average winning trade percent (for Kelly)
            avg_loss: Average losing trade percent (for Kelly)
            
        Returns:
            PositionSize object with quantity and metadata
        """
        # Validate leverage
        leverage = min(leverage, self.max_leverage)
        
        # Calculate based on method
        if self.position_size_method == PositionSizeMethod.FIXED_FRACTION:
            size_usd = account_balance * self.position_size_fraction
            risk_percent = self.position_size_fraction
            kelly_f = None
            
        elif self.position_size_method == PositionSizeMethod.KELLY:
            # Kelly Criterion: f* = (p * b - q) / b
            # where p = win rate, q = 1-p, b = avg_win/avg_loss
            if win_rate and avg_win and avg_loss and avg_loss > 0:
                b = abs(avg_win / avg_loss)
                q = 1 - win_rate
                kelly_f = (win_rate * b - q) / b
                kelly_f = max(0, min(kelly_f, 1.0))  # Clamp [0, 1]
                
                # Apply Kelly fraction (conservative scaling)
                kelly_f *= self.kelly_fraction
                size_usd = account_balance * kelly_f
                risk_percent = kelly_f
            else:
                # Fallback to fixed fraction
                logger.warning("Insufficient data for Kelly criterion, using fixed fraction")
                size_usd = account_balance * self.position_size_fraction
                risk_percent = self.position_size_fraction
                kelly_f = None
                
        elif self.position_size_method == PositionSizeMethod.FIXED_AMOUNT:
            size_usd = self.max_position_size_usd
            risk_percent = size_usd / account_balance if account_balance > 0 else 0
            kelly_f = None
            
        else:
            raise ValueError(f"Unknown position sizing method: {self.position_size_method}")
        
        # Apply maximum position size limit
        size_usd = min(size_usd, self.max_position_size_usd)
        
        # Apply minimum position size
        if size_usd < self.min_position_size_usd:
            logger.warning(f"Position size {size_usd:.2f} USD below minimum {self.min_position_size_usd}")
            size_usd = 0
            quantity = 0
        else:
            # Calculate quantity
            quantity = (size_usd * leverage) / current_price if current_price > 0 else 0
        
        return PositionSize(
            quantity=quantity,
            size_usd=size_usd,
            leverage=leverage,
            method=self.position_size_method.value,
            risk_percent=risk_percent,
            kelly_fraction=kelly_f
        )
    
    def calculate_stop_take_prices(
        self,
        entry_price: float,
        side: str
    ) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit prices
        
        Args:
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            
        Returns:
            (stop_loss_price, take_profit_price)
        """
        if side.upper() == 'BUY':
            stop_loss = entry_price * (1 - self.stop_loss_percent)
            take_profit = entry_price * (1 + self.take_profit_percent)
        else:  # SELL
            stop_loss = entry_price * (1 + self.stop_loss_percent)
            take_profit = entry_price * (1 - self.take_profit_percent)
            
        return stop_loss, take_profit
    
    def validate_trade(
        self,
        risk_metrics: RiskMetrics,
        proposed_size_usd: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if trade is allowed based on risk limits
        
        Args:
            risk_metrics: Current risk metrics
            proposed_size_usd: Proposed trade size in USD
            
        Returns:
            (is_valid, rejection_reason)
        """
        # Check emergency shutdown
        if self.emergency_shutdown:
            return False, "Emergency shutdown active"
        
        # Check circuit breaker
        if not self._check_circuit_breaker():
            return False, f"Circuit breaker open (cooldown: {self._get_cooldown_remaining():.0f}s)"
        
        # Reset daily metrics if needed
        self._reset_daily_metrics_if_needed()
        
        # Check daily trade limit
        if self.daily_trade_count >= self.max_daily_trades:
            return False, f"Daily trade limit reached ({self.max_daily_trades})"
        
        # Check daily loss limit (percent)
        if self.initial_equity:
            daily_loss_pct = abs(self.daily_pnl) / self.initial_equity
            if self.daily_pnl < 0 and daily_loss_pct > self.max_daily_loss_percent:
                return False, f"Daily loss limit exceeded ({daily_loss_pct*100:.1f}% > {self.max_daily_loss_percent*100:.1f}%)"
        
        # Check daily loss limit (absolute)
        if self.daily_pnl < -self.max_daily_loss_usd:
            return False, f"Daily loss limit exceeded (${abs(self.daily_pnl):.2f} > ${self.max_daily_loss_usd:.2f})"
        
        # Check position count limit
        if risk_metrics.open_positions >= self.max_open_positions:
            return False, f"Max open positions reached ({self.max_open_positions})"
        
        # Check total exposure limit
        new_exposure = risk_metrics.total_exposure + proposed_size_usd
        if new_exposure > self.max_total_exposure_usd:
            return False, f"Total exposure limit exceeded (${new_exposure:.2f} > ${self.max_total_exposure_usd:.2f})"
        
        # Check minimum trade interval
        if self.last_trade_time:
            time_since_last = time.time() - self.last_trade_time
            if time_since_last < self.min_trade_interval:
                remaining = self.min_trade_interval - time_since_last
                return False, f"Trade interval cooldown ({remaining:.0f}s remaining)"
        
        # Check sufficient balance
        if proposed_size_usd > risk_metrics.available_margin:
            return False, f"Insufficient margin (${risk_metrics.available_margin:.2f} < ${proposed_size_usd:.2f})"
        
        # All checks passed
        return True, None
    
    def record_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float
    ) -> Trade:
        """
        Record a new trade
        
        Args:
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            entry_price: Entry price
            quantity: Position quantity
            
        Returns:
            Trade object
        """
        trade = Trade(
            timestamp=time.time(),
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity
        )
        
        self.trades.append(trade)
        self.last_trade_time = time.time()
        self.daily_trade_count += 1
        
        logger.info(f"Trade recorded: {side} {quantity} {symbol} @ {entry_price}")
        return trade
    
    def close_trade(
        self,
        trade: Trade,
        exit_price: float
    ) -> float:
        """
        Close a trade and update metrics
        
        Args:
            trade: Trade object to close
            exit_price: Exit price
            
        Returns:
            PnL in USD
        """
        # Calculate PnL
        if trade.side.upper() == 'BUY':
            pnl = (exit_price - trade.entry_price) * trade.quantity
        else:  # SELL
            pnl = (trade.entry_price - exit_price) * trade.quantity
        
        pnl_percent = pnl / (trade.entry_price * trade.quantity) if trade.entry_price * trade.quantity > 0 else 0
        
        # Update trade
        trade.exit_price = exit_price
        trade.pnl = pnl
        trade.pnl_percent = pnl_percent
        trade.closed = True
        
        # Update metrics
        self.daily_pnl += pnl
        
        # Update consecutive losses and circuit breaker
        if pnl < 0:
            self.consecutive_losses += 1
            logger.warning(f"Loss recorded: ${pnl:.2f} ({pnl_percent*100:.2f}%), consecutive={self.consecutive_losses}")
            
            # Check circuit breaker
            if self.consecutive_losses >= self.circuit_breaker_consecutive_losses:
                self._trigger_circuit_breaker()
        else:
            logger.info(f"Win recorded: ${pnl:.2f} ({pnl_percent*100:.2f}%)")
            if self.circuit_breaker_reset_on_win:
                self.consecutive_losses = 0
        
        # Check emergency shutdown
        if self.initial_equity:
            total_loss_pct = (self.initial_equity - (self.initial_equity + self.daily_pnl)) / self.initial_equity
            if total_loss_pct >= self.emergency_shutdown_loss_percent:
                self._trigger_emergency_shutdown()
        
        return pnl
    
    def update_initial_equity(self, equity: float):
        """Set initial equity for loss calculations"""
        if self.initial_equity is None:
            self.initial_equity = equity
            logger.info(f"Initial equity set: ${equity:.2f}")
    
    def get_risk_metrics(
        self,
        total_equity: float,
        available_margin: float,
        total_exposure: float,
        open_positions: int
    ) -> RiskMetrics:
        """
        Get current risk metrics
        
        Args:
            total_equity: Total account equity
            available_margin: Available margin
            total_exposure: Total exposure in USD
            open_positions: Number of open positions
            
        Returns:
            RiskMetrics object
        """
        # Calculate win rate from closed trades
        closed_trades = [t for t in self.trades if t.closed]
        if closed_trades:
            winning_trades = sum(1 for t in closed_trades if t.pnl and t.pnl > 0)
            win_rate = winning_trades / len(closed_trades)
        else:
            win_rate = 0.0
        
        # Calculate Sharpe ratio (simplified)
        if closed_trades and len(closed_trades) > 1:
            returns = [t.pnl_percent for t in closed_trades if t.pnl_percent is not None]
            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
                sharpe = (avg_return / std_return) if std_return > 0 else 0.0
            else:
                sharpe = None
        else:
            sharpe = None
        
        return RiskMetrics(
            total_equity=total_equity,
            available_margin=available_margin,
            total_exposure=total_exposure,
            open_positions=open_positions,
            daily_pnl=self.daily_pnl,
            daily_trades=self.daily_trade_count,
            consecutive_losses=self.consecutive_losses,
            win_rate=win_rate,
            sharpe_ratio=sharpe
        )
    
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows trading"""
        if self.circuit_breaker_state == CircuitBreakerState.CLOSED:
            return True
        
        if self.circuit_breaker_state == CircuitBreakerState.OPEN:
            # Check if cooldown period has elapsed
            if self.circuit_breaker_open_time:
                elapsed = time.time() - self.circuit_breaker_open_time
                if elapsed >= self.circuit_breaker_cooldown:
                    self._reset_circuit_breaker()
                    return True
            return False
        
        return False
    
    def _trigger_circuit_breaker(self):
        """Trigger circuit breaker"""
        self.circuit_breaker_state = CircuitBreakerState.OPEN
        self.circuit_breaker_open_time = time.time()
        logger.error(f"CIRCUIT BREAKER TRIGGERED: {self.consecutive_losses} consecutive losses")
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker after cooldown"""
        self.circuit_breaker_state = CircuitBreakerState.CLOSED
        self.circuit_breaker_open_time = None
        logger.info("Circuit breaker reset")
    
    def circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is currently active (trading halted)"""
        return self.circuit_breaker_state == CircuitBreakerState.OPEN
    
    def _get_cooldown_remaining(self) -> float:
        """Get remaining cooldown time"""
        if self.circuit_breaker_open_time:
            elapsed = time.time() - self.circuit_breaker_open_time
            return max(0, self.circuit_breaker_cooldown - elapsed)
        return 0
    
    def _trigger_emergency_shutdown(self):
        """Trigger emergency shutdown"""
        self.emergency_shutdown = True
        logger.critical(f"EMERGENCY SHUTDOWN TRIGGERED: Loss exceeds {self.emergency_shutdown_loss_percent*100:.1f}%")
    
    def _reset_daily_metrics_if_needed(self):
        """Reset daily metrics at start of new day"""
        current_time = time.time()
        time_since_reset = current_time - self.daily_reset_time
        
        # Reset at midnight or after 24 hours
        if time_since_reset >= 86400:  # 24 hours
            logger.info(f"Resetting daily metrics: trades={self.daily_trade_count}, pnl=${self.daily_pnl:.2f}")
            self.daily_reset_time = current_time
            self.daily_pnl = 0.0
            self.daily_trade_count = 0
    
    def get_statistics(self) -> Dict:
        """Get comprehensive risk statistics"""
        closed_trades = [t for t in self.trades if t.closed]
        
        if not closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'sharpe_ratio': None
            }
        
        winning_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl and t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in closed_trades if t.pnl)
        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0.0
        
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        largest_win = max((t.pnl for t in winning_trades), default=0.0)
        largest_loss = min((t.pnl for t in losing_trades), default=0.0)
        
        # Sharpe ratio
        if len(closed_trades) > 1:
            returns = [t.pnl_percent for t in closed_trades if t.pnl_percent is not None]
            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
                sharpe = (avg_return / std_return * math.sqrt(252)) if std_return > 0 else 0.0
            else:
                sharpe = None
        else:
            sharpe = None
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'sharpe_ratio': sharpe,
            'consecutive_losses': self.consecutive_losses,
            'circuit_breaker_state': self.circuit_breaker_state.value,
            'emergency_shutdown': self.emergency_shutdown,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trade_count
        }
