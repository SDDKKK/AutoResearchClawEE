# Scientific Visualization Guidelines

> Publication-quality figure creation for ResearchClaw project.

## Overview

This project generates research figures (literature analysis, benchmark comparisons, pipeline performance, ablation studies). All figures should be publication-ready with proper formatting, colorblind-safe palettes, and correct export settings.

## Library Stack

| Library | Use case |
|---------|----------|
| matplotlib | Multi-panel layouts, fine-grained control |
| seaborn | Statistical plots, distribution comparisons |
| plotly | Interactive exploration (not for final figures) |

## Quick Start

```python
import matplotlib.pyplot as plt
import matplotlib as mpl

# Publication defaults
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "SimHei"],
    "font.size": 8,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
})
```

## Color Palettes

### Default: Okabe-Ito (colorblind-safe)

```python
OKABE_ITO = [
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#000000",  # black
]
plt.rcParams["axes.prop_cycle"] = plt.cycler(color=OKABE_ITO)
```

### Rules

- **Always** use colorblind-safe palettes (Okabe-Ito or seaborn `"colorblind"`)
- **Heatmaps**: use perceptually uniform colormaps (`viridis`, `plasma`, `cividis`)
- **Diverging data**: use `RdBu_r` or `PuOr`, centered at 0
- **Never** use `jet` or `rainbow`
- **Add redundant encoding** when color alone distinguishes categories: line styles, markers

```python
line_styles = ["-", "--", "-.", ":"]
markers = ["o", "s", "^", "v"]
```

## Figure Dimensions

Common figure widths (in inches):

| Layout | Width | Typical use |
|--------|-------|-------------|
| Single column | 3.5 | One plot |
| 1.5 column | 5.5 | Medium multi-panel |
| Double column | 7.0 | Full-width multi-panel |

```python
fig, ax = plt.subplots(figsize=(3.5, 2.5))
```

## Common Plot Patterns

### Bar/Line Plot with Error Bars

```python
fig, ax = plt.subplots(figsize=(3.5, 2.5))
ax.errorbar(x, means, yerr=sems, fmt="o-", capsize=3, label="F1-score")
ax.set_xlabel("Year")
ax.set_ylabel("F1-score")
ax.legend(frameon=False)
```

### Statistical Comparison (seaborn)

```python
import seaborn as sns

sns.set_theme(style="ticks", context="paper", font_scale=1.1)
sns.set_palette("colorblind")

fig, ax = plt.subplots(figsize=(3.5, 3))
sns.boxplot(data=df, x="model", y="score", palette="Set2", ax=ax)
sns.stripplot(data=df, x="model", y="score",
              color="black", alpha=0.3, size=3, ax=ax)
ax.set_ylabel("Score")
sns.despine()
```

### Heatmap (correlation matrix)

```python
import numpy as np

fig, ax = plt.subplots(figsize=(5, 4))
corr = df_numeric.corr()
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt=".2f",
            cmap="RdBu_r", center=0, square=True,
            linewidths=1, cbar_kws={"shrink": 0.8}, ax=ax)
plt.tight_layout()
```

### Multi-Panel Figure

```python
from string import ascii_uppercase

fig = plt.figure(figsize=(7, 4))
gs = fig.add_gridspec(2, 2, hspace=0.4, wspace=0.4)
axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]

for i, ax in enumerate(axes):
    ax.text(-0.15, 1.05, ascii_uppercase[i], transform=ax.transAxes,
            fontsize=10, fontweight="bold", va="top")

# Panel A: line plot
# Panel B: bar plot
# ... fill each panel

plt.tight_layout()
```

### Time Series with Confidence Band (seaborn)

```python
fig, ax = plt.subplots(figsize=(5, 3))
sns.lineplot(data=timeseries, x="year", y="saidi",
             hue="model", errorbar=("ci", 95),
             markers=True, ax=ax)
ax.set_xlabel("Year")
ax.set_ylabel("F1-score")
sns.despine()
```

## Chinese Character Support

This project involves Chinese labels (模型名称, 指标 etc.). Ensure font fallback:

```python
mpl.rcParams["font.sans-serif"] = ["Arial", "SimHei", "Microsoft YaHei"]
mpl.rcParams["axes.unicode_minus"] = False  # fix minus sign display
```

## Export

### Formats

| Format | Use |
|--------|-----|
| PDF | Vector, for manuscripts and reports |
| PNG | Raster, for slides and web (300 DPI) |
| TIFF | Raster, required by some journals |

**Never use JPEG** for plots (lossy compression creates artifacts).

### Export Code

```python
fig.savefig("figures/figure1.pdf", bbox_inches="tight")
fig.savefig("figures/figure1.png", dpi=300, bbox_inches="tight")
```

## Statistical Rigor

When displaying data:
- **Always include error bars** (SD, SEM, or CI — specify which in caption)
- **Show individual data points** when n is small
- **Mark statistical significance** with `*`, `**`, `***`
- **Report sample size** (n) in figure or caption

## Checklist Before Saving Figure

- [ ] Colorblind-safe palette used
- [ ] All axes labeled with units
- [ ] Font size >= 7 pt at final print size
- [ ] Top/right spines removed (unless needed)
- [ ] Error bars present with type specified
- [ ] Chinese characters render correctly
- [ ] Saved as PDF (vector) or PNG (300 DPI)
- [ ] No chart junk (unnecessary gridlines, 3D effects)
