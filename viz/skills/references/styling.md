# Library Selection and Styling

## Library Selection

### Use Seaborn When:
- Statistical distributions (histogram + KDE, violin, box plots)
- Regression with confidence intervals
- Categorical comparisons with error bars
- Heatmaps and correlation matrices

### Use Matplotlib When:
- Fine-grained control over appearance
- Time series with date formatting
- Custom annotations and reference lines
- Simple plots without statistical features

### Combine Both:
Use seaborn for the statistical plot, matplotlib for customizations like reference lines.

## Publication Quality Standards

- **Labels**: Descriptive axis labels with units, 12pt+ font
- **Titles**: Clear, informative, 14pt+ font
- **Figure size**: `figsize=(10, 6)` or appropriate aspect ratio
- **Layout**: Always use `tight_layout()` to prevent clipping
- **Grids**: Subtle guidance with `alpha=0.3`
- **Colors**: Colorblind-friendly palettes (viridis, coolwarm, Set2)
- **Transparency**: Alpha for overlapping points
- **Imports**: Inside the script for self-contained execution
