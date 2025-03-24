import yfinance as yf
import pandas as pd
from fredapi import Fred

from utils.frontend_utils import search_stocks


def get_adj_close_from_stocks(stocks, start_date, end_date):
    """
        Extract Adjusted Close from mentioned stocks on specific dates
        Adj Close => Closing price adjusted 
                    for splits and dividend distributions
    """
    adj_close_df = pd.DataFrame()
    
    for s in stocks:
        data = yf.download(s, start=start_date, end=end_date, auto_adjust=False)
        adj_close_df[s] = data['Adj Close']
    
    return adj_close_df


def get_risk_free_rate():
    """
        Returns the Risk Free Rate based on Federal
        Risk Free Rate => theoretical rate of return received on zero-risk assets
    """
    fred = Fred(api_key="e9048dc2c26dae67bc75a443cd644ce3")
    ten_year_treasury_rate = fred.get_series_latest_release('GS10') / 100
    risk_free_rate = ten_year_treasury_rate.iloc[-1]
    return risk_free_rate

def create_bounds(min_weights : list, max_weights : list):
    """
        Create bounds for the min. and max. a stock can have
    """
    bounds = []
    for i in range (len(max_weights)):
        if (min_weights[i] > max_weights[i] or max_weights[i] == 0.0):
            bounds.append((0.0, 1))
        else:
            bounds.append((min_weights[i], max_weights[i]))
    return bounds

def get_portfolio_return(tickers, weights, start_date, end_date):
    """
        Returns :
        - Portfolio returns over a time range
        - Dataframe with cumulative returns for each period
    """
    tickers = [
        search_stocks(ticker.strip()) if not ticker.isalpha() else ticker
        for ticker in tickers
    ]
    data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=False)[
        "Adj Close"
    ]
    returns = data.pct_change().dropna()
    portfolio_returns = (returns * weights).sum(axis=1)

    cumulative_returns = (1 + portfolio_returns).cumprod() - 1
    # first one => to plot over time
    # second => final return over the time period
    return cumulative_returns.iloc[-1] * 100, cumulative_returns
