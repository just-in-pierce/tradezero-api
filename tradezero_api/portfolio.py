from __future__ import annotations

import warnings
from typing import overload, Optional, Literal

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from .enums import PortfolioTab, OrderType


class Portfolio:
    def __init__(self, driver: WebDriver):
        self.driver = driver

    @overload
    def portfolio(self, return_type: Literal['df'] = 'df') -> Optional[pd.DataFrame]:
        ...

    @overload
    def portfolio(self, return_type: Literal['dict']) -> Optional[dict]:
        ...

    def portfolio(self, return_type: Literal['df', 'dict'] = 'df') -> pd.DataFrame | dict | None:
        """
        return the Portfolio table as a pandas.DataFrame or nested dict, with the symbol column as index.
        the column names are the following: 'type', 'qty', 'p_close', 'entry',
        'price', 'change', '%change', 'day_pnl', 'pnl', 'overnight'
        note that if the portfolio is empty Pandas won't be able to locate the table,
        and therefore will return None

        :param return_type: 'df' or 'dict'
        :return: pandas.DataFrame or None if table empty
        """
        portfolio_symbols = self.driver.find_elements(By.XPATH, '//*[@id="opTable-1"]/tbody/tr/td[1]')
        df = pd.read_html(self.driver.page_source, attrs={'id': 'opTable-1'}, keep_default_na=False)[0]

        if len(portfolio_symbols) == 0 or df.loc[0, 0].lower() == "you have no open positions.":
            warnings.warn('Portfolio is empty')
            return None

        df.columns = [
            'symbol', 'type', 'qty', 'p_close', 'entry', 'price', 'change', '%change', 'day_pnl', 'pnl', 'overnight'
        ]
        if return_type == 'dict':
            return df.to_dict('index')
        return df

    def open_orders(self) -> pd.DataFrame:
        """
        return DF with only positions that were opened today (intraday positions)

        :return: pandas.DataFrame
        """
        df = self.portfolio()

        # if there are no open position: return an empty dataframe
        if df is None:
            return pd.DataFrame()

        filt = df['overnight'] == 'Yes'
        return df.loc[~filt]

    def invested(self, symbol) -> bool:
        """
        returns True if the given symbol is in portfolio, else: false

        :param symbol: str: e.g: 'aapl', 'amd', 'NVDA', 'GM'
        :return: bool
        """
        data = self.portfolio('dict')
        if data is None:
            return False

        return symbol.upper() in data.keys()

    def _switch_portfolio_tab(self, tab: PortfolioTab) -> None:
        """
        Switch the focus to a given tab

        Note that this is idem-potent, meaning you can switch twice consecutively in the same tab.

        :param tab: enum of PortfolioTab
        :return: None
        """
        portfolio_tab = self.driver.find_element(By.ID, tab)
        portfolio_tab.click()

    def get_active_orders(self, return_type: str = 'df'):
        """
        Get a dataframe with all the active orders and their info

        :param return_type: 'df' or 'dict'
        :return: dataframe or dictionary (based on the return_type parameter)
        """
        active_orders = self.driver.find_elements(By.XPATH, '//*[@id="aoTable-1"]/tbody/tr[@order-id]')
        if len(active_orders) == 0:
            warnings.warn('There are no active orders')
            return

        df = pd.read_html(self.driver.page_source, attrs={'id': 'aoTable-1'}, keep_default_na=False)[0]
        df = df.drop(0, axis=1)  # remove the first column which contains the button "CANCEL"
        df.columns = ['ref_number', 'symbol', 'side', 'qty', 'open', 'exec', 'type', 'status', 'tif', 'limit', 'stop', 'placed']

        if return_type == 'dict':
            return df.to_dict('index')
        return df

    def symbol_present_in_active_orders(self, symbol: str) -> bool:
        """
        Check if a given symbol is present in the active orders tab

        :param symbol:
        :return: True or False
        """
        active_orders = self.get_active_orders()
        if active_orders is None:
            return False
        elif symbol.upper() in active_orders['symbol'].values:
            return True
        else:
            warnings.warn(f'Symbol {symbol} is not present in active orders')
            return False

    def cancel_active_orders(self, symbol: str, order_ref_numbers: list) -> None:
        """
        Cancel a pending orders

        :param symbol:
        :param order_type: enum of OrderType - NotImplemented
        :return: None
        """
        symbol = symbol.upper()
        self._switch_portfolio_tab(tab=PortfolioTab.active_orders)

        # find the ref-id of all the orders we have to cancel:
        order_ref_numbers = [x[x.find("S.s:", x.find("S.s:") + 1):] for x in order_ref_numbers]
        ids_to_cancel = order_ref_numbers
        ids_to_cancel = [x.replace('S.', '') for x in ids_to_cancel]

        for order_id in ids_to_cancel:
            try:
                cancel_button = self.driver.find_element(
                    By.XPATH, f'//div[@id="portfolio-content-tab-ao-1"]//*[@order-id="{order_id}"]/td[@class="red"]')
                cancel_button.click()
            except:
                print(f'Could not cancel order with ref number {order_id} for symbol {symbol}. It may have already been executed or canceled.')

    def get_active_order_ref_numbers_ticker(self, symbol: str) -> list:
        """
        Get the reference numbers of all active orders for a given symbol

        :param symbol: str
        :return: list of order reference numbers
        """
        self._switch_portfolio_tab(tab=PortfolioTab.active_orders)
        active_orders = self.get_active_orders()

        if active_orders is None:
            return []

        symbol = symbol.upper()
        order_ref_numbers = active_orders[active_orders['symbol'] == symbol]['ref_number'].values.tolist()
        return order_ref_numbers
    
    def get_locate_inventory(self, return_type: str = 'df') -> pd.DataFrame:
        """
        Get the locate inventory as a DataFrame

        :return: pandas.DataFrame with locate inventory
        """

        located_symbols = self.driver.find_elements(By.XPATH, '//*[@id="locate-inventory-table"]/tbody/tr/td[1]')
        if len(located_symbols) == 0:
            warnings.warn('Locate inventory is empty')
            return pd.DataFrame()
        
        df = pd.read_html(self.driver.page_source, attrs={'id': 'locate-inventory-table'}, keep_default_na=False)[0]
        df.columns = ['symbol', 'tooltip', 'available', 'unavailable', "empty", "action"]
        # drop tooltip and action columns
        df = df.drop(columns=['tooltip', 'empty', "action"])

        if return_type == 'dict':
            return df.to_dict('index')
        return df