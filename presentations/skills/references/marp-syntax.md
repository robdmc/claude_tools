# Marp Syntax Quick Reference

## Frontmatter

```yaml
---
marp: true
theme: default
paginate: true
header: 'Header text'
footer: 'Footer text'
style: |
  /* Custom CSS here */
---
```

## Slide Separation

Use `---` on its own line to create a new slide:

```markdown
# Slide 1

Content

---

# Slide 2

More content
```

## Directives

### Global Directives (in frontmatter)

```yaml
marp: true          # Enable Marp
theme: default      # Theme: default, gaia, uncover
paginate: true      # Show page numbers
header: 'Text'      # Header on all slides
footer: 'Text'      # Footer on all slides
backgroundColor: #fff
color: #333
```

### Local Directives (per slide)

```markdown
<!-- _class: title -->        # Apply CSS class to this slide
<!-- _backgroundColor: #000 --> # Background for this slide
<!-- _color: white -->          # Text color for this slide
<!-- _paginate: false -->       # Hide page number on this slide
<!-- _header: '' -->            # Remove header on this slide
```

## Images

### Basic

```markdown
![](image.png)
```

### Sizing

```markdown
![w:500](image.png)           # Width 500px
![h:400](image.png)           # Height 400px
![w:600 h:400](image.png)     # Both dimensions
```

### Background Images

```markdown
![bg](background.jpg)          # Full background
![bg left](image.jpg)          # Left half background
![bg right:40%](image.jpg)     # Right 40% background
![bg contain](image.jpg)       # Contain (no crop)
![bg cover](image.jpg)         # Cover (may crop)
![bg fit](image.jpg)           # Fit within slide
![bg 50%](image.jpg)           # 50% size
```

### Multiple Backgrounds

```markdown
![bg](image1.jpg)
![bg](image2.jpg)
```

## Text Formatting

```markdown
**bold**
*italic*
~~strikethrough~~
`inline code`
[link](url)
```

## Lists

```markdown
- Bullet point
- Another point
  - Nested point

1. Numbered item
2. Another item
```

## Code Blocks

````markdown
```python
def hello():
    print("Hello")
```
````

## Tables

```markdown
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |
```

## Math (LaTeX)

```markdown
Inline: $E = mc^2$

Block:
$$
\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
$$
```

## HTML in Slides

Marp supports inline HTML:

```markdown
<div style="display: flex; gap: 20px;">
  <div>Column 1</div>
  <div>Column 2</div>
</div>
```

## Fragments (Incremental Reveal)

```markdown
* First point
* Second point <!-- This appears with first -->

---

* Third point <!-- New slide needed for reveal -->
```

Note: True fragments require HTML presentation mode, not PDF.

## Scoped Styles

Apply CSS to just one slide:

```markdown
---

<style scoped>
h2 { color: red; }
</style>

## This Title is Red

Only on this slide.
```

## Comments / Speaker Notes

```markdown
<!--
These are speaker notes.
They appear in presenter view but not on slides.
-->
```

## Emoji

```markdown
:smile: :rocket: :100:
```

## Escaping

```markdown
\* Not italic \*
\--- Not a slide break
```
