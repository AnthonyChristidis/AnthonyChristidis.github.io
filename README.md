# anthonychristidis.github.io

Personal website of Anthony Christidis, PhD.

Plain static HTML + CSS, no build step. Pages:

| File | Page |
| --- | --- |
| `index.html` | Home |
| `background.html` | Background |
| `publications.html` | Publications |
| `software.html` | Software |
| `teaching.html` | Teaching |
| `books.html` | Books |

Shared design tokens (colors, type, spacing) live at the top of `styles.css`.
The sticky sidebar and top nav are duplicated in each page - if you change one,
change them all; the only per-page difference is the `aria-current="page"`
attribute on the active nav link.

Preview locally by opening any `.html` file in a browser, or:

    python -m http.server 8000
