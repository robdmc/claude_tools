# Slide Element Patterns

HTML patterns for common slide elements. Slide agents should use these patterns when generating slide HTML. All patterns follow the html2pptx constraints (no unwrapped div text, no bg on text elements, web-safe fonts only, etc.).

---

## Slide Title

```html
<h2 class="slide-title">Revenue Analysis</h2>
```

---

## Bullet List

```html
<ul>
  <li>Revenue grew 15% YoY</li>
  <li>North region outperformed</li>
</ul>
```

---

## Numbered List

```html
<ol>
  <li>First action item</li>
  <li>Second action item</li>
</ol>
```

---

## Callout Box

```html
<div class="callout"><p>42% increase in revenue YoY</p></div>
```

---

## Image

Viz and image references are resolved during the asset step and copied to `./assets/`.

```html
<img src="./assets/revenue-chart.png" />
```

---

## Block Quote

```html
<blockquote>
  <p>"The best way to predict the future is to create it."</p>
  <p>— Peter Drucker</p>
</blockquote>
```

---

## Table

```html
<table>
  <thead>
    <tr><th>Metric</th><th>Q3</th><th>Q4</th><th>Change</th></tr>
  </thead>
  <tbody>
    <tr><td>Revenue</td><td>$3.8M</td><td>$4.2M</td><td>+11%</td></tr>
    <tr><td>Customers</td><td>420</td><td>523</td><td>+25%</td></tr>
  </tbody>
</table>
```

---

## Speaker Notes

Strip entirely from HTML — speaker notes do not appear in the slide.

---

## Diagram

Diagrams use a hybrid approach: HTML `<div>` elements for boxes/labels/backgrounds (html2pptx converts these to native PowerPoint shapes), plus a PptxGenJS code snippet for connectors, arrows, and lines.

**All text inside `<div>` must be wrapped in `<p>` tags** (html2pptx rejects unwrapped text in divs):

```html
<div style="display:flex; align-items:center; gap:16pt; margin-top:40pt; justify-content:center;">
  <div style="background:#4472C4; padding:12pt 20pt; border-radius:4pt;"><p style="color:white; font-weight:bold; margin:0;">Input</p></div>
  <div style="background:#4472C4; padding:12pt 20pt; border-radius:4pt;"><p style="color:white; font-weight:bold; margin:0;">Process</p></div>
  <div style="background:#4472C4; padding:12pt 20pt; border-radius:4pt;"><p style="color:white; font-weight:bold; margin:0;">Output</p></div>
</div>
```

PptxGenJS snippet (returned alongside HTML, for connectors/arrows added post-conversion):
```javascript
// Arrow from Input → Process (colors without # prefix)
slide.addShape(pptx.ShapeType.rightArrow, { x: 2.8, y: 2.2, w: 0.6, h: 0.35, fill: { color: "4472C4" } });
// Arrow from Process → Output
slide.addShape(pptx.ShapeType.rightArrow, { x: 5.3, y: 2.2, w: 0.6, h: 0.35, fill: { color: "4472C4" } });
```

**Key rule:** html2pptx converts `<div>` boxes and `<p>` labels to native PowerPoint shapes automatically. PptxGenJS snippets handle only connectors, arrows, and lines — elements that cannot be represented by simple HTML layout.
