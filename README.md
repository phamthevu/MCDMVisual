# MCDMVisualStudio

Desktop app for visualizing final DEMATEL and MCDM ranking results and inspecting imported regression / SEM outputs.

## App tabs

- **Data:** select the input type, import one workbook/CSV, choose an Excel worksheet when needed, and preview the imported values.
- **Visual:** DEMATEL influence network, prominence–relation quadrants, influence heatmap, prominence ranking, and final ranking charts. Hover over points, cells, and links to see the underlying values. Keep zoom while changing chart settings or chart type; use `+` / `−` and set tick spacing while the data determines the visible range. Drag the splitter between settings and preview to give either side more room. Add infinite horizontal `y = c` and vertical `x = c` references, or a full-chart function `y = ax + b`. The editor separates `c` from `a` and `b`, and locks parameters that do not apply to the selected line. Configure line color, opacity (1–50), and dash pattern (0–50). Choose primary and secondary colors for the other chart types; DEMATEL Cause and Effect markers have separate shape and color controls. The chart legend is hidden by default; enable it, then manage existing items or add your own using editable symbol and standard-name dropdowns. The **Arrows** panel configures influence interval color, opacity (1–50), dash pattern (0–50), and arrowhead size (1–50 px).
- **Quantitative Charts:** uses the data imported from **Data**; there is no second import button. Select Regression, CB-SEM, or PLS-SEM in Data, import the matching worksheet, and the corresponding analysis tab unlocks. Regression provides observed-vs-fitted, residuals-vs-fitted, and coefficient charts. CB-SEM and PLS-SEM provide path diagrams with directional arrowheads, coefficient charts, and imported metric charts. Hover over observations, estimates, paths, and constructs for details; choose primary and secondary colors for the charts.

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

The UI tests include removal of the XY Drawing tab, SEM arrowheads and hover data, configurable chart colors, infinite horizontal/vertical lines and clipped full-chart function lines, arrow opacity/dash/size ranges, legend dropdowns, Cause/Effect marker settings, import-mode gating, resizable settings/preview layout, and zoom retention while switching charts:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```
