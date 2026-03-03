## Visualization Preferences for Marimo Notebooks

When creating visualizations inside marimo notebooks, use this order of preference:

1. **hvplot** (preferred) — built on HoloViews/Bokeh, interactive by default
2. **holoviews** — when you need more control than hvplot provides
3. **matplotlib** — last resort; must be wrapped for interactivity

All visualizations must be interactive.

### hvplot

```python
import hvplot.pandas  # or hvplot.polars
df.hvplot.scatter(x="col_a", y="col_b")
```

hvplot outputs are interactive by default — no extra wrapping needed.

### holoviews

```python
import holoviews as hv
hv.extension("bokeh")
hv.Scatter(df, kdims=["col_a"], vdims=["col_b"])
```

HoloViews with the Bokeh backend is interactive by default.

### matplotlib (wrap with mo.mpl.interactive)

When matplotlib is unavoidable, call `mo.mpl.interactive()` at the top of the cell before plotting, then use `plt.gca()` as the last expression:

```python
import marimo as mo
import matplotlib.pyplot as plt

mo.mpl.interactive()

plt.figure()
plt.plot(x, y)
plt.title("My Plot")
plt.gca()
```
