import pandas as pd


def calc_ptList( df: pd.DataFrame, batter_side: str = None ) -> list[ str ]:
    df = df.copy()

    if batter_side is not None:
        df = df[ df[ '打席左右' ] == batter_side ]

    return df[ df[ '球種' ] != '0' ][ '球種' ].value_counts().index.tolist()
