# diagnostic: check mt_mod import from Dash._shared
import traceback
try:
    import _shared as SH
    print('Imported Dash._shared OK')
    mt = getattr(SH, 'mt_mod', None)
    print('mt_mod is None?' , mt is None)
    if mt is not None:
        print('mt_mod repr:', repr(mt))
        print('mt_mod attrs:', [a for a in dir(mt) if not a.startswith('_')][:40])
except Exception:
    print('Import failed:')
    traceback.print_exc()
