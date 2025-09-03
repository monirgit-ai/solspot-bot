from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract, case
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
from ..db import get_db
from ..models import Trade, Order, EquitySnapshot, Alert
from ..repo import TradeRepository

router = APIRouter()

@router.get("/summary")
async def get_trading_summary(
    period: str = Query("all", description="Period: all, day, week, month, year"),
    db: Session = Depends(get_db)
):
    """Get comprehensive trading summary for specified period"""
    
    try:
        # Calculate date range based on period
        end_date = datetime.now()
        if period == "day":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "year":
            start_date = end_date - timedelta(days=365)
        else:  # all
            start_date = datetime(2020, 1, 1)  # Far past date
        
        # Build query conditions
        date_condition = Trade.entry_ts >= start_date if period != "all" else True
        
        # Get completed trades
        completed_trades = db.query(Trade).filter(
            and_(
                Trade.exit_ts.isnot(None),
                date_condition
            )
        ).all()
        
        # Get open trades
        open_trades = db.query(Trade).filter(
            and_(
                Trade.exit_ts.is_(None),
                date_condition
            )
        ).all()
        
        # Calculate summary statistics
        total_trades = len(completed_trades)
        winning_trades = len([t for t in completed_trades if t.pnl_usdt and t.pnl_usdt > 0])
        losing_trades = len([t for t in completed_trades if t.pnl_usdt and t.pnl_usdt < 0])
        break_even_trades = len([t for t in completed_trades if t.pnl_usdt and t.pnl_usdt == 0])
        
        # Calculate P&L
        total_profit = sum([t.pnl_usdt for t in completed_trades if t.pnl_usdt and t.pnl_usdt > 0]) or 0
        total_loss = sum([t.pnl_usdt for t in completed_trades if t.pnl_usdt and t.pnl_usdt < 0]) or 0
        net_pnl = total_profit + total_loss
        
        # Calculate percentages
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        loss_rate = (losing_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate averages
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        avg_trade = net_pnl / total_trades if total_trades > 0 else 0
        
        # Calculate risk metrics
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
        max_drawdown = calculate_max_drawdown(completed_trades)
        
        # Get current equity
        current_equity = db.query(EquitySnapshot).order_by(EquitySnapshot.ts.desc()).first()
        current_equity_value = current_equity.equity_usdt if current_equity else 0
        
        # Calculate ROI
        initial_equity = 100.0  # From config
        roi = ((current_equity_value - initial_equity) / initial_equity * 100) if initial_equity > 0 else 0
        
        return {
            "period": period,
            "date_range": {
                "start": start_date.isoformat() if period != "all" else None,
                "end": end_date.isoformat()
            },
            "trade_summary": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "break_even_trades": break_even_trades,
                "open_trades": len(open_trades)
            },
            "performance": {
                "total_profit": round(total_profit, 2),
                "total_loss": round(total_loss, 2),
                "net_pnl": round(net_pnl, 2),
                "win_rate": round(win_rate, 2),
                "loss_rate": round(loss_rate, 2)
            },
            "averages": {
                "avg_profit": round(avg_profit, 2),
                "avg_loss": round(avg_loss, 2),
                "avg_trade": round(avg_trade, 2)
            },
            "risk_metrics": {
                "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "∞",
                "max_drawdown": round(max_drawdown, 2),
                "roi_percent": round(roi, 2)
            },
            "current_status": {
                "current_equity": round(current_equity_value, 2),
                "initial_equity": initial_equity,
                "equity_change": round(current_equity_value - initial_equity, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@router.get("/loss-analysis")
async def get_loss_analysis(
    limit: int = Query(50, description="Number of losing trades to analyze"),
    db: Session = Depends(get_db)
):
    """Analyze losing trades to identify patterns and reasons"""
    
    try:
        # Get losing trades ordered by most recent
        losing_trades = db.query(Trade).filter(
            and_(
                Trade.exit_ts.isnot(None),
                Trade.pnl_usdt < 0
            )
        ).order_by(Trade.exit_ts.desc()).limit(limit).all()
        
        if not losing_trades:
            return {"message": "No losing trades found", "analysis": {}}
        
        # Analyze exit reasons
        exit_reasons = {}
        for trade in losing_trades:
            reason = trade.reason_exit or "Unknown"
            if reason not in exit_reasons:
                exit_reasons[reason] = {"count": 0, "total_loss": 0, "trades": []}
            exit_reasons[reason]["count"] += 1
            exit_reasons[reason]["total_loss"] += abs(trade.pnl_usdt or 0)
            exit_reasons[reason]["trades"].append({
                "id": trade.id,
                "entry_time": trade.entry_ts.isoformat(),
                "exit_time": trade.exit_ts.isoformat(),
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "pnl": trade.pnl_usdt,
                "pnl_percent": trade.pnl_pct * 100 if trade.pnl_pct else 0
            })
        
        # Calculate loss patterns
        total_losses = len(losing_trades)
        avg_loss = sum([abs(t.pnl_usdt or 0) for t in losing_trades]) / total_losses
        
        # Find worst losing streak
        max_consecutive_losses = calculate_max_consecutive_losses(losing_trades)
        
        # Analyze by time of day
        time_analysis = analyze_losses_by_time(losing_trades)
        
        # Analyze by day of week
        day_analysis = analyze_losses_by_day(losing_trades)
        
        # Find most common loss scenarios
        loss_scenarios = analyze_loss_scenarios(losing_trades)
        
        return {
            "summary": {
                "total_losing_trades": total_losses,
                "average_loss": round(avg_loss, 2),
                "max_consecutive_losses": max_consecutive_losses
            },
            "exit_reasons": exit_reasons,
            "time_analysis": time_analysis,
            "day_analysis": day_analysis,
            "loss_scenarios": loss_scenarios,
            "recommendations": generate_loss_recommendations(exit_reasons, loss_scenarios)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing losses: {str(e)}")

@router.get("/detailed-trades")
async def get_detailed_trades(
    period: str = Query("all", description="Period: all, day, week, month, year"),
    trade_type: str = Query("all", description="Trade type: all, winning, losing, open"),
    limit: int = Query(100, description="Maximum number of trades to return"),
    db: Session = Depends(get_db)
):
    """Get detailed trade information with filtering"""
    
    try:
        # Calculate date range
        end_date = datetime.now()
        if period == "day":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "year":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime(2020, 1, 1)
        
        # Build query
        query = db.query(Trade)
        
        # Apply date filter
        if period != "all":
            query = query.filter(Trade.entry_ts >= start_date)
        
        # Apply trade type filter
        if trade_type == "winning":
            query = query.filter(and_(Trade.exit_ts.isnot(None), Trade.pnl_usdt > 0))
        elif trade_type == "losing":
            query = query.filter(and_(Trade.exit_ts.isnot(None), Trade.pnl_usdt < 0))
        elif trade_type == "open":
            query = query.filter(Trade.exit_ts.is_(None))
        
        # Get trades ordered by entry time
        trades = query.order_by(Trade.entry_ts.desc()).limit(limit).all()
        
        # Format trade data
        trade_data = []
        for trade in trades:
            trade_info = {
                "id": trade.id,
                "symbol": trade.symbol,
                "entry_time": trade.entry_ts.isoformat(),
                "entry_price": trade.entry_price,
                "quantity": trade.qty,
                "stop_loss": trade.sl,
                "take_profit": trade.tp1,
                "status": "open" if trade.exit_ts is None else "closed"
            }
            
            if trade.exit_ts:
                trade_info.update({
                    "exit_time": trade.exit_ts.isoformat(),
                    "exit_price": trade.exit_price,
                    "pnl_usdt": trade.pnl_usdt,
                    "pnl_percent": trade.pnl_pct * 100 if trade.pnl_pct else 0,
                    "exit_reason": trade.reason_exit,
                    "duration_hours": round((trade.exit_ts - trade.entry_ts).total_seconds() / 3600, 2)
                })
            
            trade_data.append(trade_info)
        
        return {
            "period": period,
            "trade_type": trade_type,
            "total_trades": len(trade_data),
            "trades": trade_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving trades: {str(e)}")

@router.get("/performance-chart")
async def get_performance_chart(
    period: str = Query("30d", description="Period: 7d, 30d, 90d, 1y"),
    db: Session = Depends(get_db)
):
    """Get performance data for charting"""
    
    try:
        # Calculate date range
        end_date = datetime.now()
        if period == "7d":
            start_date = end_date - timedelta(days=7)
            group_by = "hour"
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
            group_by = "day"
        elif period == "90d":
            start_date = end_date - timedelta(days=90)
            group_by = "day"
        elif period == "1y":
            start_date = end_date - timedelta(days=365)
            group_by = "week"
        else:
            start_date = end_date - timedelta(days=30)
            group_by = "day"
        
        # Get equity snapshots
        snapshots = db.query(EquitySnapshot).filter(
            EquitySnapshot.ts >= start_date
        ).order_by(EquitySnapshot.ts).all()
        
        # Get trades for P&L calculation
        trades = db.query(Trade).filter(
            and_(
                Trade.exit_ts.isnot(None),
                Trade.exit_ts >= start_date
            )
        ).all()
        
        # Group data by time period
        chart_data = group_performance_data(snapshots, trades, group_by, start_date, end_date)
        
        return {
            "period": period,
            "group_by": group_by,
            "data": chart_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating chart data: {str(e)}")

# Helper functions
def calculate_max_drawdown(trades: List[Trade]) -> float:
    """Calculate maximum drawdown from peak"""
    if not trades:
        return 0.0
    
    # Sort trades by entry time
    sorted_trades = sorted(trades, key=lambda x: x.entry_ts)
    
    peak_equity = 100.0  # Initial equity
    max_drawdown = 0.0
    current_equity = 100.0
    
    for trade in sorted_trades:
        if trade.pnl_usdt:
            current_equity += trade.pnl_usdt
            if current_equity > peak_equity:
                peak_equity = current_equity
            
            drawdown = (peak_equity - current_equity) / peak_equity * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    
    return max_drawdown

def calculate_max_consecutive_losses(trades: List[Trade]) -> int:
    """Calculate maximum consecutive losing trades"""
    if not trades:
        return 0
    
    max_streak = 0
    current_streak = 0
    
    for trade in trades:
        if trade.pnl_usdt and trade.pnl_usdt < 0:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    
    return max_streak

def analyze_losses_by_time(trades: List[Trade]) -> Dict[str, Any]:
    """Analyze losses by time of day"""
    time_slots = {
        "00:00-06:00": {"count": 0, "total_loss": 0},
        "06:00-12:00": {"count": 0, "total_loss": 0},
        "12:00-18:00": {"count": 0, "total_loss": 0},
        "18:00-24:00": {"count": 0, "total_loss": 0}
    }
    
    for trade in trades:
        hour = trade.entry_ts.hour
        if 0 <= hour < 6:
            slot = "00:00-06:00"
        elif 6 <= hour < 12:
            slot = "06:00-12:00"
        elif 12 <= hour < 18:
            slot = "12:00-18:00"
        else:
            slot = "18:00-24:00"
        
        time_slots[slot]["count"] += 1
        time_slots[slot]["total_loss"] += abs(trade.pnl_usdt or 0)
    
    # Calculate averages
    for slot in time_slots:
        if time_slots[slot]["count"] > 0:
            time_slots[slot]["avg_loss"] = round(time_slots[slot]["total_loss"] / time_slots[slot]["count"], 2)
        else:
            time_slots[slot]["avg_loss"] = 0
    
    return time_slots

def analyze_losses_by_day(trades: List[Trade]) -> Dict[str, Any]:
    """Analyze losses by day of week"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_analysis = {day: {"count": 0, "total_loss": 0} for day in days}
    
    for trade in trades:
        day_name = trade.entry_ts.strftime("%A")
        day_analysis[day_name]["count"] += 1
        day_analysis[day_name]["total_loss"] += abs(trade.pnl_usdt or 0)
    
    # Calculate averages
    for day in day_analysis:
        if day_analysis[day]["count"] > 0:
            day_analysis[day]["avg_loss"] = round(day_analysis[day]["total_loss"] / day_analysis[day]["count"], 2)
        else:
            day_analysis[day]["avg_loss"] = 0
    
    return day_analysis

def analyze_loss_scenarios(trades: List[Trade]) -> Dict[str, Any]:
    """Analyze common loss scenarios"""
    scenarios = {
        "quick_losses": {"count": 0, "total_loss": 0},  # < 1 hour
        "medium_losses": {"count": 0, "total_loss": 0},  # 1-6 hours
        "long_losses": {"count": 0, "total_loss": 0},    # > 6 hours
        "large_losses": {"count": 0, "total_loss": 0},   # > 2% loss
        "small_losses": {"count": 0, "total_loss": 0}    # < 0.5% loss
    }
    
    for trade in trades:
        if trade.exit_ts and trade.pnl_usdt:
            # Duration analysis
            duration = (trade.exit_ts - trade.entry_ts).total_seconds() / 3600
            if duration < 1:
                scenarios["quick_losses"]["count"] += 1
                scenarios["quick_losses"]["total_loss"] += abs(trade.pnl_usdt)
            elif duration < 6:
                scenarios["medium_losses"]["count"] += 1
                scenarios["medium_losses"]["total_loss"] += abs(trade.pnl_usdt)
            else:
                scenarios["long_losses"]["count"] += 1
                scenarios["long_losses"]["total_loss"] += abs(trade.pnl_usdt)
            
            # Loss size analysis
            loss_pct = abs(trade.pnl_pct or 0) * 100
            if loss_pct > 2:
                scenarios["large_losses"]["count"] += 1
                scenarios["large_losses"]["total_loss"] += abs(trade.pnl_usdt)
            elif loss_pct < 0.5:
                scenarios["small_losses"]["count"] += 1
                scenarios["small_losses"]["total_loss"] += abs(trade.pnl_usdt)
    
    # Calculate averages
    for scenario in scenarios:
        if scenarios[scenario]["count"] > 0:
            scenarios[scenario]["avg_loss"] = round(scenarios[scenario]["total_loss"] / scenarios[scenario]["count"], 2)
        else:
            scenarios[scenario]["avg_loss"] = 0
    
    return scenarios

def generate_loss_recommendations(exit_reasons: Dict, loss_scenarios: Dict) -> List[str]:
    """Generate recommendations based on loss analysis"""
    recommendations = []
    
    # Analyze exit reasons
    if "Stop Loss" in exit_reasons and exit_reasons["Stop Loss"]["count"] > 0:
        sl_count = exit_reasons["Stop Loss"]["count"]
        if sl_count > 5:
            recommendations.append("High number of stop loss hits - consider widening stop losses or improving entry timing")
    
    # Analyze loss scenarios
    if loss_scenarios["quick_losses"]["count"] > loss_scenarios["long_losses"]["count"]:
        recommendations.append("Many quick losses suggest poor entry timing - review entry conditions")
    
    if loss_scenarios["large_losses"]["count"] > 0:
        recommendations.append("Large losses detected - review position sizing and risk management")
    
    if not recommendations:
        recommendations.append("Loss patterns look normal - continue monitoring for improvements")
    
    return recommendations

def group_performance_data(snapshots: List[EquitySnapshot], trades: List[Trade], 
                          group_by: str, start_date: datetime, end_date: datetime) -> List[Dict]:
    """Group performance data for charting"""
    # This is a simplified version - you can enhance it based on your charting needs
    chart_data = []
    
    # Group by time period and calculate cumulative P&L
    current_date = start_date
    cumulative_pnl = 0
    
    while current_date <= end_date:
        # Find trades in this period
        period_trades = [t for t in trades if t.exit_ts and 
                        current_date <= t.exit_ts < current_date + timedelta(days=1)]
        
        period_pnl = sum([t.pnl_usdt or 0 for t in period_trades])
        cumulative_pnl += period_pnl
        
        chart_data.append({
            "date": current_date.isoformat(),
            "period_pnl": round(period_pnl, 2),
            "cumulative_pnl": round(cumulative_pnl, 2),
            "trade_count": len(period_trades)
        })
        
        if group_by == "hour":
            current_date += timedelta(hours=1)
        elif group_by == "day":
            current_date += timedelta(days=1)
        elif group_by == "week":
            current_date += timedelta(weeks=1)
    
    return chart_data
