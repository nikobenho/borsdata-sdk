from json import loads
from time import sleep
from typing import List

from requests import get

from .models.Branch import Branch
from .models.Instrument import Instrument
from .models.InstrumentUpdate import InstrumentUpdate
from .models.Market import Market
from .models.Sector import Sector
from .models.StockPrice import StockPrice
from .models.Country import Country

RATE_LIMIT = 429
RATE_WAIT = .3
UPDATED = True


class BorsdataAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self._params = {'authKey': self.api_key}
        self._uri = 'https://apiservice.borsdata.se'
        self._version = 'v1'
        self._root = '{host}/{version}/'.format(
            host=self._uri, version=self._version)

    def get_markets(self) -> List[Market]:
        """Returns all markets.

        Returns:
            List[Market] -- List of markets.
        """

        self._markets = [Market(**market)
                         for market in self._get_data_object('markets')]

        return self._markets

    def get_branches(self):
        return [Branch(**branch) for branch in self._get_data_object('branches')]

    def get_sectors(self) -> List[Sector]:
        """Returns all sectors.

        Returns:
            List[Sector] -- List of sectors.
        """

        return [Sector(**sector) for sector in self._get_data_object('sectors')]

    def get_countries(self):
        return [Country(**country) for country in self._get_data_object('countries')]

    def get_instruments(self, markets=None) -> List[Instrument]:
        """Returns all instruments.

        Keyword Arguments:
            markets {int[]} -- Id list of markets used to filter the resulting list (default: {None}).

        Returns:
            List[Instrument] -- List of instruments.
        """

        instruments = [Instrument(**instrument)
                       for instrument in self._get_data_object('instruments')]

        if markets is None:
            return instruments

        filtered_instruments = []

        for instrument in instruments:
            if instrument.marketId in markets:
                filtered_instruments.append(instrument)

        return filtered_instruments

    def get_instruments_updated(self) -> List[InstrumentUpdate]:
        """Returns all updated instruments.

        Returns:
            List[InstrumentUpdate] -- List of all updated instruments.
        """

        _, data = self._get('instruments/updated')

        return [InstrumentUpdate(**instrument) for instrument in data.get('instruments')]

    def get_instrument_stock_price(self, ins_id, start=None, end=None) -> List[StockPrice]:
        """Returns stockprices for an instrument (ins_id), it is possible to determine the timespan using start and end. Max 10 years, if no time filters provided.

        Arguments:
            ins_id {int} -- Instrument id.

        Keyword Arguments:
            start {str} --  Determines from which day to start the collection, ex: '2009-04-22' (default: {None})
            end {str} -- Determines the collection limit, ex:'2009-04-25' (default: {None})

        Raises:
            IOError: Is thrown if the API responds with anything other than 200.

        Returns:
            List[StockPrice] -- List of the collected stockprices.
        """

        params = self._params.copy()

        while True:
            if start and end:
                params.update({'from': start, 'to': end})

            res = get(self._root + 'instruments/{}/stockprices'.format(ins_id),
                      params=params, verify=False)

            if res.status_code != 200 and not res.status_code == RATE_LIMIT:
                raise IOError(
                    'Failed to communicate with the borsdata_sdk api')

            if res.status_code == 200:
                break

            sleep(0.3)

        entries = [StockPrice(**entry)
                   for entry in loads(res.content).get('stockPricesList')]

        return entries

    def get_instrument_stock_price_last(self) -> List[StockPrice]:
        """Returns Last StockPrices for all instruments.

        Returns:
            List[StockPrice] -- List of all last updated price entries for each instrument.
        """

        status, data = self._get('instruments/stockprices/last')

        return [StockPrice(**entry) for entry in data.get('stockPricesList', [])]

    def _get_data_object(self, data_type):
        """Gets the specified datatype from the remote API.

        Arguments:
            data_type {str} -- Datatype.

        Raises:
            IOError: Is thrown if the API responds with anything other than 200.

        Returns:
            List[T] - List of the passed type.
        """

        status, data = self._get(data_type)

        if status != 200:
            raise IOError(
                f'Failed to communicate with {self._root}{data_type} status: {status}')

        return data.get(data_type)

    def _get(self, endpoint) -> (int, dict):
        """Perform a remote request to the API and retries on rate limit responses, returns json payload on success.

        Arguments:
            endpoint {str} -- endpoint to access, ex: `instruments/StockSplits`.

        Returns:
            (int, dict) -- The first entry, holds the status code of the response; the second, holds the response content parsed from json.
        """

        while True:
            res = get(self._root + endpoint, self._params, verify=False)

            if res.status_code != RATE_LIMIT:
                break

            sleep(RATE_WAIT)

        return res.status_code, res.json()
