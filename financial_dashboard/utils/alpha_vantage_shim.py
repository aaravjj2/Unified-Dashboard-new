"""Compatibility shim for alpha_vantage SectorPerformances.

Some environments ship a different API; this shim tries to import the real
class and otherwise provides a lightweight stub with the same interface used
by the dashboard (get_sector or get_sector_overview).
"""
try:
    # Try to import the common class name (different versions vary)
    from alpha_vantage.sectorperformance import SectorPerformances as _RealSector
except Exception:
    try:
        # Older/newer versions might expose via alphavantage module
        from alpha_vantage.alphavantage import SectorPerformances as _RealSector
    except Exception:
        _RealSector = None


class SectorPerformances:
    def __init__(self, key=None, output_format='pandas'):
        self.key = key
        self.output_format = output_format
        if _RealSector:
            try:
                self._real = _RealSector(key=key, output_format=output_format)
            except Exception:
                self._real = None
        else:
            self._real = None

    def get_sector(self):
        """Return sector performance DataFrame-like tuple (data, meta) or stub.

        If the real alpha_vantage is present, delegate. Otherwise return an
        empty DataFrame and a meta dict.
        """
        if self._real:
            try:
                return self._real.get_sector()
            except Exception:
                pass
        # Fallback: return empty pandas DataFrame-like structure
        try:
            import pandas as pd
            df = pd.DataFrame()
            meta = {'Note': 'alpha_vantage sector data not available in this environment.'}
            return df, meta
        except Exception:
            return {}, {'Note': 'alpha_vantage sector data not available.'}

    # For possible alternate method names
    def get_sector_overview(self):
        return self.get_sector()
