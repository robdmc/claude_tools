# Graph Styling for Presentations

Guidelines for creating matplotlib graphs that look professional in Marp presentations.

## Standard Setup

```python
import matplotlib.pyplot as plt
import numpy as np

# Use clean style
plt.style.use('seaborn-v0_8-whitegrid')

# Configure for presentations
plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'savefig.facecolor': 'white',
    'font.size': 14,
    'axes.titlesize': 18,
    'axes.labelsize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 12,
    'figure.titlesize': 20,
    'axes.spines.top': False,
    'axes.spines.right': False,
})
```

## Color Palette

Professional colors that work well on white backgrounds:

```python
COLORS = [
    '#2563eb',  # Blue (primary)
    '#dc2626',  # Red
    '#16a34a',  # Green
    '#9333ea',  # Purple
    '#f97316',  # Orange
    '#06b6d4',  # Cyan
]

# For sequential data
BLUE_GRADIENT = ['#dbeafe', '#93c5fd', '#3b82f6', '#1d4ed8', '#1e3a8a']
```

## Standard Figure Sizes

```python
# Standard graph (works with ![w:700])
fig, ax = plt.subplots(figsize=(10, 6))

# Wide graph (works with ![w:900])
fig, ax = plt.subplots(figsize=(12, 5))

# Square graph
fig, ax = plt.subplots(figsize=(8, 8))

# Side-by-side subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
```

## Saving Graphs

Always save to `.viz/` directory:

```python
import os

# Ensure .viz directory exists
os.makedirs('.viz', exist_ok=True)

# Save with tight layout and high DPI
plt.tight_layout()
plt.savefig('.viz/graph_name.png', dpi=150, bbox_inches='tight')
plt.close()
```

## Graph Types

### Bar Graph

```python
fig, ax = plt.subplots(figsize=(10, 6))
categories = ['A', 'B', 'C', 'D']
values = [25, 40, 30, 55]

bars = ax.bar(categories, values, color=COLORS[0], edgecolor='white', linewidth=1.5)
ax.set_ylabel('Value')
ax.set_title('Bar Graph Title')

# Add value labels on bars
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            str(val), ha='center', va='bottom', fontsize=12)
```

### Line Graph

```python
fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(10)
y1 = np.random.randn(10).cumsum()
y2 = np.random.randn(10).cumsum()

ax.plot(x, y1, color=COLORS[0], linewidth=2.5, marker='o', label='Series A')
ax.plot(x, y2, color=COLORS[1], linewidth=2.5, marker='s', label='Series B')
ax.legend()
ax.set_xlabel('X Label')
ax.set_ylabel('Y Label')
ax.set_title('Line Graph Title')
```

### Pie Graph

```python
fig, ax = plt.subplots(figsize=(8, 8))
sizes = [35, 25, 20, 20]
labels = ['Category A', 'Category B', 'Category C', 'Category D']

ax.pie(sizes, labels=labels, colors=COLORS[:4], autopct='%1.0f%%',
       startangle=90, explode=[0.02]*4)
ax.set_title('Pie Graph Title')
```

### Horizontal Bar Graph

```python
fig, ax = plt.subplots(figsize=(10, 6))
categories = ['Item A', 'Item B', 'Item C', 'Item D', 'Item E']
values = [85, 72, 68, 55, 42]

bars = ax.barh(categories, values, color=COLORS[0])
ax.set_xlabel('Value')
ax.set_title('Horizontal Bar Graph')

# Add value labels
for bar, val in zip(bars, values):
    ax.text(val + 1, bar.get_y() + bar.get_height()/2,
            str(val), va='center', fontsize=12)
```

## Integration with Presentations

Reference saved graphs in Marp slides:

```markdown
---

## Analysis Results

![w:700](../.viz/my_graph.png)

Key finding: The data shows a clear upward trend.
```

## Tips

1. **Keep it simple** - Remove unnecessary gridlines and decorations
2. **Use consistent colors** - Stick to the color palette across all graphs
3. **Large fonts** - Ensure readability when projected
4. **White background** - Matches the slide background
5. **Clear titles** - Every graph should have a descriptive title
6. **Legend placement** - Keep legends from overlapping data
7. **Tight layout** - Use `bbox_inches='tight'` to avoid clipping
