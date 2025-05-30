import marimo

__generated_with = "0.13.13"
app = marimo.App(width="full")


@app.cell
def _():
    import polars as pl
    import plotly.express as px
    # from sklearn.linear_model import LinearRegression
    import numpy as np
    import statsmodels.api as sm

    return np, pl, px, sm


@app.cell
def _(pl):
    # load the chm data

    df = pl.read_parquet("output\\calc_stats\\rehab_chm_stats.parquet")

    df
    return (df,)


@app.cell
def _(df, pl):
    # choose a pre-2015 area

    df_pre_2015 = df.filter(pl.col('short_id') == 'b9ceaa')

    df_pre_2015.sort('date')
    return (df_pre_2015,)


@app.cell
def _(df_pre_2015, px):
    _fig = px.line(
        df_pre_2015
        , x = 'date'
        , y = 'p90_height_m'
        , template = 'plotly_white'
        , title = 'P90 Height Over Time for Area b9ceaa'
    
    )
    _fig.update_layout(yaxis_title='P90 Height (m)', xaxis_title=None)
    _fig.show()
    return


@app.cell
def _(df_pre_2015, px):
    _fig = px.line(
        df_pre_2015
        , x = 'date'
        , y = 'woody_cover'
        , template = 'plotly_white'
        , title = '% Woody Cover (>1m) for Area b9ceaa'
        , hover_data={'woody_cover': ':.1%' }
    )
    _fig.update_layout(yaxis_title='Woody Cover %', xaxis_title=None)
    _fig.update_yaxes(tickformat='0%')
    _fig.show()
    return


@app.cell
def _(df, pl, px):
    _df = (df
            .filter((pl.col('veg_type') != 'pasture') & (pl.col('rehab_year') < 2021))
            .sort(by=['short_id', 'date'])
          )

    _n_categories = _df.select('short_id').unique().height
    _n_cols = 3  # facet_col_wrap value
    _n_rows = (_n_categories + _n_cols - 1) // _n_cols


    _fig = px.line(
        _df
        , x = 'date'
        , y = 'p90_height_m'
        , facet_col = 'short_id'
        , facet_col_wrap = _n_cols
        # , facet_row_wrap = _n_rows
        , template = 'plotly_white'
        , title = 'P90 Height Over Time for Area b9ceaa'
        , height=400*_n_rows
        , facet_row_spacing = 0.005
    )
    _fig.update_layout(yaxis_title=None, xaxis_title=None)

    _fig.show()
    # _n_categories
    return


@app.cell
def _(df, np, pl, sm):


    # Convert date to numeric (days since epoch) & filter
    df_with_numeric_date = (
        df
        .with_columns([
            pl.col("date").dt.epoch(time_unit="d").alias("date_numeric")
        ])
        .filter((pl.col('veg_type') != 'pasture') & (pl.col('rehab_year') < 2021))
        .filter(pl.col("area_m2_from_chm") > 10000)
    )
    def fit_ols_regression(group_data):
        """Fit OLS regression using statsmodels and return key statistics"""
        # Get the short_id for this group (should be the same for all rows)
        short_id = group_data["short_id"][0]
    
        date_numeric = group_data["date_numeric"].to_numpy()
        height = group_data["p90_height_m"].to_numpy()
    
        if len(date_numeric) < 2:
            return pl.DataFrame({
                "short_id": [short_id],
                "slope_m_per_day": [None],
                "intercept": [None], 
                "r_squared": [None],
                "p_value": [None],
                "std_error": [None]
            })
    
        # Remove NaN values
        mask = ~(np.isnan(date_numeric) | np.isnan(height))
        if mask.sum() < 2:
            return pl.DataFrame({
                "short_id": [short_id],
                "slope_m_per_day": [None],
                "intercept": [None], 
                "r_squared": [None],
                "p_value": [None],
                "std_error": [None]
            })
    
        date_clean = date_numeric[mask]
        height_clean = height[mask]
    
        # Add constant term for intercept
        X_with_const = sm.add_constant(date_clean)
    
        try:
            # Fit the model
            model = sm.OLS(height_clean, X_with_const)
            results = model.fit()
        
            # Extract results
            intercept = results.params[0]
            slope = results.params[1]
            r_squared = results.rsquared
            p_value = results.pvalues[1]  # p-value for the slope
            std_err = results.bse[1]  # standard error for the slope
        
            return pl.DataFrame({
                "short_id": [short_id],
                "slope_m_per_day": [slope],
                "intercept": [intercept], 
                "r_squared": [r_squared],
                "p_value": [p_value],
                "std_error": [std_err]
            })
        except:
            return pl.DataFrame({
                "short_id": [short_id],
                "slope_m_per_day": [None],
                "intercept": [None], 
                "r_squared": [None],
                "p_value": [None],
                "std_error": [None]
            })

    df_with_numeric_date

    # Apply OLS regression for each short_id
    results = (
        df_with_numeric_date
        .group_by("short_id")
        .map_groups(fit_ols_regression)
        .with_columns([
            # Convert slope from m/day to m/year
            (pl.col("slope_m_per_day") * 365.25).alias("growth_rate_m_per_year"),
            # Convert standard error from m/day to m/year
            (pl.col("std_error") * 365.25).alias("std_error_m_per_year")
        ])
        .select([
            "short_id", 
            "growth_rate_m_per_year", 
            "intercept", 
            "r_squared",
            "p_value",
            "std_error_m_per_year"
        ])
    )

    res = (results
        .filter(pl.col("growth_rate_m_per_year") > 0)
        .sort("growth_rate_m_per_year", descending=True)
    )

    res
    return (res,)


@app.cell
def _(px, res):
    px.scatter(
        res
        , x='short_id'
        , y='growth_rate_m_per_year'
        , template='plotly_white'
    )
    return


if __name__ == "__main__":
    app.run()
