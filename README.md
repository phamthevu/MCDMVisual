# MCDMVisualStudio

Desktop app for visualizing final DEMATEL and MCDM ranking results, drawing freeform XY figures, and inspecting imported regression / SEM outputs.

## App tabs

- **Data:** select the input type, import one workbook/CSV, choose an Excel worksheet when needed, and preview the imported values.
- **Visual:** DEMATEL influence network, prominence–relation quadrants, influence heatmap, prominence ranking, and final ranking charts. Keep zoom while changing chart settings or chart type; use `+` / `−` and set tick spacing while the data determines the visible range. Manage colored `x=k` / `y=k` reference lines in one dialog. For DEMATEL networks, choose Cause and Effect marker shapes and colors. The chart legend is hidden by default; enable it, then manage or remove existing items and add your own descriptions. The **Arrows** panel sets each influence interval's opacity, line style, and color.
- **XY Drawing:** separate blank XY canvas with a PowerPoint-style toolbar. Drag on the canvas to size rectangles, ellipses, triangles, and arrows; click to place a default-size shape. Type a label and click **Add text**, then drag the label to reposition it. Configure text background, border, and colors; double-click an object's name to rename it, or select it and press **Delete**. Use **Lock view**, `+`, and `−` to control the canvas.
- **Quantitative Charts:** uses the data imported from **Data**; there is no second import button. Select Regression, CB-SEM, or PLS-SEM in Data, import the matching worksheet, and the corresponding analysis tab unlocks. Regression provides observed-vs-fitted, residuals-vs-fitted, and coefficient charts. CB-SEM and PLS-SEM provide path diagrams, coefficient charts, and imported metric charts.

The quantitative charts visualize imported outputs. Regression's OLS line is calculated for visual diagnostics. CB-SEM and PLS-SEM models and measurement validity indices are not estimated by this application.

## Data formats

### DEMATEL

Import the **final total influence matrix T**. The first row contains factor names, the first column repeats them in the same order, and inner cells contain numeric values. The app calculates R, C, R+C, R−C, normalized prominence weight `(R+C)/sum(R+C)`, rank, and cause/effect group.

### Ranking

Import alternatives in the first column and one or more numeric final score/rank columns after it. Lower-is-better defaults apply to rank, distance, cost, error, and loss metrics.

### Regression

Choose Regression in Data and import a sheet with numeric predictor X and observed Y columns. The preview stays in Data; choose the desired chart in the unlocked Regression page.

### CB-SEM / PLS-SEM

Choose CB-SEM or PLS-SEM in Data and import a sheet with `Source`, `Target`, and numeric `Estimate` columns for a structural path diagram. For measurement/validity metric charts, use one row per metric with a text label and numeric value. Existing p-values, confidence intervals, alpha, CR, AVE, or HTMT values can remain in the workbook; this tool only plots supplied values.

## Template and demo files

- `Template/`: blank colored Excel input sheets.
- `Demo Data/`: populated DEMATEL, ranking, regression, and SEM examples.

## Run from source

Python 3.10 or newer is recommended.

```bash
python -m pip install -r requirements.txt
python -m app.main
```

On Windows, run `setup_windows.bat` once and then `run_windows.bat`.

## Build Windows application

Run `build_windows.bat`. It creates `.build-venv`, installs dependencies and PyInstaller, and generates an onedir application under `dist/MCDMVisualStudio/`. The PyInstaller spec packages `Template/` and `Demo Data/`.

## Test

The UI tests include drag-to-draw shapes and arrows, arrowhead geometry and color, text positioning and styling, object renaming/deletion, PNG/SVG rendering, legend/reference management, Cause/Effect marker settings, import-mode gating, axis panel sizing, and zoom retention while switching charts:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```
