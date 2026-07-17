"""
Unified GTFS-NeTEx calendar comparison method.

This module defines ONE matching rule, applied identically to every country in
this project. It exists to replace the six different per-country matching
criteria that were used in the original per-country notebooks (Austria,
Luxembourg, France, Norway, Sweden, Italy), which ranged from a pure day-by-day
pattern comparison (Norway, Sweden, Italy) to a four-field comparison that also
required first/last active date to agree (Luxembourg, France) to a
summary-only comparison that never checked individual days at all (Austria).

Matching rule used here (fixed, the same for every country):
Two calendar patterns -- one from GTFS, one from NeTEx -- are considered the
same pattern if, and only if, their day-by-day activity pattern is identical
within the shared comparison window. That is: for every single day in the
window, both patterns agree on whether the service is active that day.

No other field is used to decide a match. In particular, total active-day
count, first active date, and last active date are NOT part of the matching
key -- they are computed and reported for descriptive purposes only, since
using them (as the original Luxembourg/France notebooks did) can make the
match artificially stricter when one feed's calendar extends further outside
the shared window than the other's (see the France_MVD.ipynb notebook for a
worked example of this effect).

How to use this module for a new country:
1. Build `gtfs_dates_by_id`: a dict mapping each GTFS calendar identifier
   (usually `service_id`) to the set of dates on which it is active.
2. Build `netex_dates_by_id`: a dict mapping each NeTEx calendar identifier
   (e.g. `daytype_ref` or `operating_period_id`) to the set of dates on which
   it is active.
   How these two dictionaries are built is expected to differ by country,
   since GTFS and NeTEx calendar structures are not represented the same way
   in every published dataset (see the DATA4PT GTFS-NeTEx mapping, which shows
   a GTFS calendar record can correspond to different NeTEx structures
   depending on the implementation). That extraction step is intentionally
   NOT standardized by this module.
3. Call `compare_calendar_patterns(gtfs_dates_by_id, netex_dates_by_id)`.
   This applies the same matching rule regardless of how the two dictionaries
   were produced.
"""

import numpy as np
import pandas as pd


def build_activity_pattern(active_dates, comparison_dates):
    """
    Encode a set of dates as a binary string over a fixed comparison window.

    Parameters
    ----------
    active_dates : iterable of dates
        The dates on which the service/pattern is active.
    comparison_dates : pandas.DatetimeIndex
        The full comparison window, one entry per day, in order.

    Returns
    -------
    str
        A string of '1'/'0' characters, one per day in `comparison_dates`,
        where '1' means the service is active that day and '0' means it is not.

    Implementation note: this uses a numpy offset-array approach rather than a
    per-day membership check, since some countries' comparison windows span
    thousands of days across tens of thousands of ids (e.g. Norway spans a
    2,989-day window over ~25,000 ids) -- a naive day-by-day string build is
    too slow at that scale.
    """
    window_start = comparison_dates[0]
    window_days = len(comparison_dates)

    normalized = pd.to_datetime(list(active_dates)).normalize()
    if len(normalized) == 0:
        return "0" * window_days

    offsets = (normalized - window_start).days.values
    valid = (offsets >= 0) & (offsets < window_days)
    offsets = offsets[valid]

    bits = np.zeros(window_days, dtype=np.uint8)
    bits[offsets] = 1
    return "".join(bits.astype(str))


def _offsets_to_pattern_string(offsets, window_days):
    """Convert a sorted array/tuple of day-offsets into a '1'/'0' bit string."""
    bits = np.zeros(window_days, dtype=np.uint8)
    if len(offsets):
        bits[np.asarray(offsets)] = 1
    return "".join(bits.astype(str))


def build_pattern_table(dates_by_id, comparison_dates, id_col_name):
    """
    Turn a dict of {id: set of active dates} into a pattern-level table.

    For each id, restricts its active dates to the comparison window, then
    builds the day-by-day activity_pattern string. IDs with zero active days
    inside the window are dropped, since an all-zero pattern does not
    represent an actual service pattern for comparison purposes.

    Parameters
    ----------
    dates_by_id : dict
        Mapping from a calendar identifier to a set/iterable of active dates.
    comparison_dates : pandas.DatetimeIndex
        The shared comparison window.
    id_col_name : str
        Name to use for the identifier column in the returned DataFrame
        (e.g. "gtfs_service_id" or "netex_daytype_ref").

    Returns
    -------
    pandas.DataFrame
        Columns: [id_col_name, n_active_days_window, first_active_date_window,
        last_active_date_window, activity_pattern]. The last three descriptive
        columns are NOT used for matching -- only activity_pattern is.

    Implementation note: this is fully vectorized rather than looping in
    Python once per id, since some countries have tens of thousands of ids
    (e.g. Norway has ~25,000 GTFS+NeTEx calendar ids combined) -- a per-id
    Python loop, even with vectorized work inside it, is too slow purely from
    Python-level call overhead at that scale. Instead, every id's dates are
    flattened into one long (id, date) table, offsets are computed once for
    the whole table, and ids are grouped back together with pandas' own
    vectorized groupby -- then activity_pattern strings are built only once
    per *unique* offset-tuple (pattern), not once per id.
    """
    window_start = comparison_dates[0]
    window_days = len(comparison_dates)

    # Flatten to one row per (id, date) pair.
    ids_col = []
    dates_col = []
    for entity_id, active_dates in dates_by_id.items():
        active_dates = list(active_dates)
        ids_col.extend([entity_id] * len(active_dates))
        dates_col.extend(active_dates)

    if not ids_col:
        return pd.DataFrame(columns=[
            id_col_name, "n_active_days_window", "first_active_date_window",
            "last_active_date_window", "activity_pattern",
        ])

    long_df = pd.DataFrame({id_col_name: ids_col, "date": pd.to_datetime(dates_col).normalize()})
    long_df["offset"] = (long_df["date"] - window_start).dt.days
    long_df = long_df[(long_df["offset"] >= 0) & (long_df["offset"] < window_days)]

    if long_df.empty:
        return pd.DataFrame(columns=[
            id_col_name, "n_active_days_window", "first_active_date_window",
            "last_active_date_window", "activity_pattern",
        ])

    grouped = long_df.groupby(id_col_name).agg(
        n_active_days_window=("offset", "size"),
        first_active_date_window=("date", "min"),
        last_active_date_window=("date", "max"),
        offset_tuple=("offset", lambda s: tuple(sorted(s))),
    ).reset_index()

    # Build the activity_pattern string once per unique offset_tuple, then map
    # it back onto every id sharing that pattern -- much cheaper than building
    # a window_days-long string separately for every single id.
    unique_offset_tuples = grouped["offset_tuple"].unique()
    pattern_lookup = {
        ot: _offsets_to_pattern_string(ot, window_days) for ot in unique_offset_tuples
    }
    grouped["activity_pattern"] = grouped["offset_tuple"].apply(lambda t: pattern_lookup[t])
    grouped = grouped.drop(columns=["offset_tuple"])

    return grouped


def compare_calendar_patterns(gtfs_dates_by_id, netex_dates_by_id,
                               shared_start=None, shared_end=None):
    """
    Compare GTFS and NeTEx calendar patterns using the unified matching rule.

    The comparison window is, by default, the overlap between the earliest
    and latest active dates seen on each side (the "shared window" approach
    already used for Norway, Sweden, and Italy). It can be overridden by
    passing shared_start/shared_end explicitly, e.g. to match a country's
    documented feed validity window instead of inferring it from the data.

    Parameters
    ----------
    gtfs_dates_by_id : dict
        {gtfs calendar id: set of active dates}
    netex_dates_by_id : dict
        {netex calendar id: set of active dates}
    shared_start, shared_end : optional
        Explicit comparison window bounds. If not given, computed as the
        overlap of both feeds' actual active-date ranges.

    Returns
    -------
    dict
        Summary statistics (all JSON/print-friendly, no DataFrames), plus
        'gtfs_patterns_df' and 'netex_patterns_df' for further inspection.
    """
    # Flatten once, then normalize the whole batch in a single vectorized call
    # (calling pd.to_datetime per-id here, inside the comprehension, is the
    # same per-id overhead problem described in build_pattern_table -- avoid it).
    all_gtfs_dates_raw = [d for dates in gtfs_dates_by_id.values() for d in dates]
    all_netex_dates_raw = [d for dates in netex_dates_by_id.values() for d in dates]

    all_gtfs_dates = pd.to_datetime(all_gtfs_dates_raw).normalize()
    all_netex_dates = pd.to_datetime(all_netex_dates_raw).normalize()

    gtfs_min_date, gtfs_max_date = all_gtfs_dates.min(), all_gtfs_dates.max()
    netex_min_date, netex_max_date = all_netex_dates.min(), all_netex_dates.max()

    if shared_start is None:
        shared_start = max(gtfs_min_date, netex_min_date)
    else:
        shared_start = pd.Timestamp(shared_start)

    if shared_end is None:
        shared_end = min(gtfs_max_date, netex_max_date)
    else:
        shared_end = pd.Timestamp(shared_end)

    comparison_dates = pd.date_range(shared_start, shared_end, freq="D")

    gtfs_patterns_df = build_pattern_table(gtfs_dates_by_id, comparison_dates, "gtfs_id")
    netex_patterns_df = build_pattern_table(netex_dates_by_id, comparison_dates, "netex_id")

    gtfs_pattern_set = set(gtfs_patterns_df["activity_pattern"])
    netex_pattern_set = set(netex_patterns_df["activity_pattern"])
    matched_patterns = gtfs_pattern_set & netex_pattern_set

    n_gtfs = len(gtfs_pattern_set)
    n_netex = len(netex_pattern_set)
    n_matched = len(matched_patterns)

    return {
        "gtfs_earliest_active_date": gtfs_min_date,
        "gtfs_latest_active_date": gtfs_max_date,
        "netex_earliest_active_date": netex_min_date,
        "netex_latest_active_date": netex_max_date,
        "shared_start_date": shared_start,
        "shared_end_date": shared_end,
        "window_days": len(comparison_dates),
        "gtfs_ids_total": len(gtfs_dates_by_id),
        "netex_ids_total": len(netex_dates_by_id),
        "gtfs_unique_patterns": n_gtfs,
        "netex_unique_patterns": n_netex,
        "matched_patterns": n_matched,
        "gtfs_match_rate_pct": round(n_matched / n_gtfs * 100, 2) if n_gtfs else 0.0,
        "netex_match_rate_pct": round(n_matched / n_netex * 100, 2) if n_netex else 0.0,
        "gtfs_patterns_df": gtfs_patterns_df,
        "netex_patterns_df": netex_patterns_df,
    }


def summary_row(country_name, result):
    """Reduce a compare_calendar_patterns() result to one flat row for a combined table."""
    return {
        "country": country_name,
        "shared_window_days": result["window_days"],
        "gtfs_unique_patterns": result["gtfs_unique_patterns"],
        "netex_unique_patterns": result["netex_unique_patterns"],
        "matched_patterns": result["matched_patterns"],
        "gtfs_match_rate_pct": result["gtfs_match_rate_pct"],
        "netex_match_rate_pct": result["netex_match_rate_pct"],
    }
