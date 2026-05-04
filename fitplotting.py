# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "numpy",
#     "matplotlib",
#     "seaborn",
#     "asyncio",
#     "typer",
# ]
# ///
import pathlib
import re
from typing import Annotated, Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import typer
import traceback


def find_sets_of_files(directory: pathlib.Path) -> dict[
    str, dict[Literal["data_sim", "residuals", "residuals-bitmap", "report", "diagnostics", "histogram", "RI_Noise", "TI_Noise"], pathlib.Path]]:
    """Find all the files in the directory and return a dictionary of sets of files for each triple and fit type"""
    sets_of_files: dict[
        str, dict[Literal["data_sim", "residuals", "residuals-bitmap", "report", "diagnostics", "histogram", "RI_Noise", "TI_Noise"],
        pathlib.Path]] \
        = {}
    for file in directory.glob("**/*"):
        if not file.suffix in [".csv", ".html", ".txt"]:
            continue
        # Standardize triple extraction
        base = file.stem.rsplit("-", 1)[0]
        base = re.sub(r"-3D-s$", "", base)
        base = re.sub(r"-residuals$", "", base)
        if not base in sets_of_files:
            sets_of_files[base] = {}
        file_type = file.stem
        prefix = file_type.replace(base + "-", "")
        if prefix == "data_sim":
            sets_of_files[base]["data_sim"] = file
        elif prefix == "report":
            sets_of_files[base]["report"] = file
        elif prefix == "diagnostics":
            sets_of_files[base]["diagnostics"] = file
        elif prefix == "histogram":
            sets_of_files[base]["histogram"] = file
        elif prefix == "residuals":
            sets_of_files[base]["residuals"] = file
        elif prefix == "residuals-bitmap":
            sets_of_files[base]["residuals-bitmap"] = file
        elif prefix == "TI_Noise":
            sets_of_files[base]["TI_Noise"] = file
        elif prefix == "RI_Noise":
            sets_of_files[base]["RI_Noise"] = file
        else:
            continue
    output: dict[str, dict[Literal["data_sim", "residuals", "residuals-bitmap", "report", "diagnostics", "histogram", "RI_Noise", "TI_Noise"], pathlib.Path]] = {}
    required_files = ["data_sim", "residuals", "report", "diagnostics"]
    for triple, files in sets_of_files.items():
        if all(file in files for file in required_files):
            output[triple] = files
    return output

def parse_report(report_file: pathlib.Path) -> dict:
    """Parse the html report file and return a dictionary of the fit parameters"""
    data = {}
    with report_file.open("r") as f:
        html = f.read()
    
    # Extract Analytic Method
    method_match = re.search(r"<h1>(.*?)</h1>", html)
    data["analytic_method"] = method_match.group(1).strip() if method_match else "Unknown Method"

    # extract the data analysis settings table
    start_index = html.find("<h3>Data Analysis Settings:</h3>")
    if start_index != -1:
        end_index = html.find("</table>", start_index)
        if end_index != -1:
            table_html = html[start_index:end_index]
            pattern = r"<tr><td>(.*?)</td><td>(.*?)</td></tr>"
            matches = re.findall(pattern, table_html)
            for key, value in matches:
                data[key.strip(" :")] = value.strip()

    # extract metadata
    run_match = re.search(r"Data Report for Run \"(.*?)\",", html)
    data["run_name"] = run_match.group(1) if run_match else "Unknown Run"
    
    cell_match = re.search(r"Cell (\d+),", html)
    data["cell"] = cell_match.group(1) if cell_match else "?"
    
    channel_match = re.search(r"Channel (\w+),", html)
    data["channel"] = channel_match.group(1) if channel_match else "?"
    
    wavelength_match = re.search(r"Wavelength (\d+),", html)
    data["wavelength"] = wavelength_match.group(1) if wavelength_match else "?"
    
    edit_match = re.search(r"Edited Dataset ([\d\w_-]+)</h2>", html)
    data["edit_name"] = edit_match.group(1) if edit_match else "Unknown Edit"
    
    data["triple"] = f"{data['cell']}/{data['channel']}/{data['wavelength']}"
    
    return data

def parse_diagnostics(diagnostics_file: pathlib.Path) -> dict:
    data = {}
    with diagnostics_file.open("r") as f:
        text = f.read()
    
    keys = ["Excess Kurtosis", "KS Statistic", "H Metric", "Runs Test Z", "Runs Test p", "Runs Observed", "Durbin-Watson"]
    values = re.findall(r"\s*([\w\s]+):\s+([\w\.\-+]+)\s*\n", text)
    for key, value in values:
        if key in keys:
            data[key] = value
    return data

def load_data_sim(file_path: pathlib.Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(file_path)
    df.columns = [col.strip(" \"\n") for col in df.columns]
    # Identify data vs simulation columns
    data_cols = [c for c in df.columns if "S-Curve" not in c]
    sim_cols = [c for c in df.columns if "S-Curve" in c]
    
    return df[data_cols], df[sim_cols]

def load_residuals(file_path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    # remove " in column names
    df.columns = [col.strip(" \"\n") for col in df.columns]
    return df

def load_ti_noise(file_path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    df.columns = [col.strip(" \"\n") for col in df.columns]
    return df

def load_ri_noise(file_path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    df.columns = [col.strip(" \"\n") for col in df.columns]
    return df

def plot_signal(ax: plt.Axes, data_df: pd.DataFrame, sim_df: pd.DataFrame, metadata: dict):
    """Plot experimental data as points and simulation as lines"""
    # Number of curves
    num_curves = len(data_df.columns) // 2
    colors = sns.color_palette("Spectral", num_curves)
    
    for i in range(num_curves):
        r_col = data_df.columns[2*i]
        v_col = data_df.columns[2*i + 1]
        
        # Drop NaNs for plotting
        valid = data_df[[r_col, v_col]].dropna()
        if not valid.empty:
            ax.scatter(valid[r_col], valid[v_col], color=colors[i], s=5, alpha=0.6)
            
    for i in range(num_curves):
        sr_col = sim_df.columns[2*i]
        sv_col = sim_df.columns[2*i + 1]
        valid_sim = sim_df[[sr_col, sv_col]].dropna()
        if not valid_sim.empty:
            # plot the simulation as black lines
            ax.plot(valid_sim[sr_col], valid_sim[sv_col], color='black', linewidth=2, alpha=0.75)

    ax.set_ylabel("Absorbance [OD]")
    title = f"{metadata.get('run_name', 'N/A')} - {metadata.get('analytic_method', 'N/A')} - {metadata.get('triple', 'N/A')}"
    ax.set_title(title)

def plot_residuals(ax: plt.Axes, res_df: pd.DataFrame, metadata: dict):
    """Plot residuals as lines"""
    # Skip the zero-line columns (0 and 1)
    num_res = (len(res_df.columns) - 2) // 2
    colors = sns.color_palette("Spectral", num_res)
    
    for i in range(num_res):
        r_col = res_df.columns[2 + 2*i]
        v_col = res_df.columns[3 + 2*i]
        valid = res_df[[r_col, v_col]].dropna()
        if not valid.empty:
            ax.scatter(valid[r_col], valid[v_col], color=colors[i], linewidth=1, alpha=0.6)
            
    ax.axhline(0, color='red', linestyle='-', linewidth=1)
    ax.set_ylabel("Residuals")
    ax.set_xlabel("Radius [cm]")
    
    rmsd = metadata.get("RMSD", "N/A")
    hmetric = metadata.get("H Metric", "N/A")
    ax.set_title(f"RMSD: {rmsd}, H-Metric: {hmetric}")
    
def plot_noise(ax: plt.Axes, ti_df: pd.DataFrame, ri_df: pd.DataFrame):
    """Plot TI and RI noise as lines, TI with left y and bottom x, RI with right y and top x"""
    # plot TI with left y and bottom x
    if not ti_df.empty:
        ax.plot(ti_df["ti_noise Radius (cm)"], ti_df["ti_noise OD Difference"], color='blue', linewidth=2, label="TI Noise")
        ax.set_xlabel("Radius [cm]")
        ax.set_ylabel("Noise [OD]")
        
    if not ri_df.empty:
        if ti_df.empty:
            ax.set_xlabel("Scan number")
            ax.set_ylabel("RI Noise [OD]")
            # plot RI noise with right y and top x
            ax.plot(ri_df["ri_noise Scan Number"], ri_df["ri_noise OD Difference"], color='red', linewidth=2, label="RI Noise")
            ax.legend(loc='upper left')
            ax.set_title("RI Noise")
        else:
            ax3 = ax.twinx()
            ax2 = ax3.twiny()
            ax2.set_xlabel("Scan number")
            ax2.set_ylabel("RI Noise [OD]")
            # make ax2 red
            ax2.spines['right'].set_color('red')
            ax2.spines['top'].set_color('red')
            ax2.tick_params(axis='y', colors='red')
            ax3.tick_params(axis='y', colors='red')
            ax2.tick_params(axis='x', colors='red')
            ax3.tick_params(axis="x", colors="blue")
            ax.spines['left'].set_color('blue')
            ax.spines['bottom'].set_color('blue')
            ax2.spines['left'].set_color('blue')
            ax2.spines['bottom'].set_color('blue')
            ax3.spines['left'].set_color('blue')
            ax3.spines['bottom'].set_color('blue')
            ax.tick_params(axis='y', colors='blue')
            ax.tick_params(axis='x', colors='blue')
            # plot RI noise with right y and top x
            ax2.plot(ri_df["ri_noise Scan Number"], ri_df["ri_noise OD Difference"], color='red', linewidth=2, label="RI Noise")
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            ax2_legend = ax2.get_legend()
            if ax2_legend:
                ax2_legend.remove()
            ax.set_title("TI and RI Noise")
    else:
        ax.set_title("TI Noise")
    sns.move_legend(
            ax, "upper center",
            bbox_to_anchor=(.5, -0.8), ncol=2, title=None, frameon=False,
    )
    

def create_combined_plot(files: dict, metadata: dict, output_path: pathlib.Path, enabled_plots: list[str] = ["signal", "residuals",
                                                                                                             "noise"]):
    try:
        data_df, sim_df = load_data_sim(files["data_sim"])
    except Exception as e:
        data_df = pd.DataFrame()
        sim_df = pd.DataFrame()
    try:
        res_df = load_residuals(files["residuals"])
    except Exception as e:
        res_df = pd.DataFrame()
    try:
        ti_df = load_ti_noise(files["TI_Noise"])
    except Exception as e:
        ti_df = pd.DataFrame()
    try:
        ri_df = load_ri_noise(files["RI_Noise"])
    except Exception as e:
        ri_df = pd.DataFrame()
    
    num_plots = len(enabled_plots)
    if num_plots == 0:
        return
    
    sns.set_context("paper", font_scale=3,)
    sns.set_style("ticks")
    sns.color_palette("Spectral", as_cmap=True)
    
    height_ratios = []
    plot_map = {}
    if "signal" in enabled_plots and not data_df.empty and not sim_df.empty:
        height_ratios.append(3)
        plot_map["signal"] = lambda ax: plot_signal(ax, data_df, sim_df, metadata)
    
    if "residuals" in enabled_plots and not res_df.empty:
        height_ratios.append(1)
        plot_map["residuals"] = lambda ax: plot_residuals(ax, res_df, metadata)
    
    if "noise" in enabled_plots and (not ti_df.empty or not ri_df.empty):
        height_ratios.append(1)
        plot_map["noise"] = lambda ax: plot_noise(ax, ti_df, ri_df)
    num_plots = len(height_ratios)
    # Create figure with shared x-axis if both are present
    fig, axes = plt.subplots(num_plots, 1, figsize=(25, 5 * num_plots),
                             sharex=True,
                             gridspec_kw={'height_ratios': height_ratios})
    
    if num_plots == 1:
        axes = [axes]
    
    for i, plot_type in enumerate(enabled_plots):
        if plot_type in plot_map:
            plot_map[plot_type](axes[i])
            
    plt.tight_layout()
    plt.savefig(output_path, format="png")
    plt.close()

def main(raw_data_dir: Annotated[pathlib.Path, typer.Argument(help="Path to the raw data directory")] = pathlib.Path.cwd() / "SV",
         output_dir: Annotated[pathlib.Path, typer.Argument(help="Path to the output directory")] = pathlib.Path.cwd() / "output" ):
    """Create a plot of the fitted data for each triple and fit type in the folder"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    sets_of_files = find_sets_of_files(raw_data_dir)
    
    for triple, files in sets_of_files.items():
        print(f"Processing {triple}")
        try:
            report_data = parse_report(files["report"])
            report_data["RMSD"] = report_data.get("RMSD", report_data.get("Residual RMS Deviation", "N/A"))
            diagnostics_data = parse_diagnostics(files["diagnostics"])
            
            # Merge metadata
            metadata = {**diagnostics_data, **report_data}
            
            output_file = output_dir / f"{triple}-plot.png"
            create_combined_plot(files, metadata, output_file)
            print(f"Saved plot to {output_file}")
        except Exception as e:
            print(f"Error processing {triple}: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
