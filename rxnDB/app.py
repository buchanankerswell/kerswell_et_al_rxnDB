import numpy as np
import pandas as pd
import seaborn as sns
from faicons import icon_svg
import matplotlib.pyplot as plt
from shiny import App, reactive, render, ui
from rxnDB.data.loader import app_dir, load_data

def get_unique_phases():
    """
    """
    df = load_data()
    reacts = pd.concat([df["reactant1"], df["reactant2"], df["reactant3"]]).unique().tolist()
    prods = pd.concat([df["product1"], df["product2"], df["product3"]]).unique().tolist()
    all_phases = list(set(reacts + prods))
    all_phases = [compound for compound in all_phases if pd.notna(compound)]
    all_phases.sort()
    all_phases = [c for c in all_phases if c != "Triple Point"]
    return all_phases

def get_max_PT_limits():
    """
    """
    df = load_data()
    return df["pmax"].max(), df["tmax"].max()

init_phases = ["Ky", "And", "Sil", "Ol", "Wd"]
phases = get_unique_phases()
P_max, T_max = get_max_PT_limits()

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_dark_mode(id="mode"),
        ui.input_checkbox_group(
            "reactants",
            "Reactants",
            phases,
            selected=init_phases,
        ),
        ui.input_checkbox_group(
            "products",
            "Products",
            phases,
            selected=init_phases,
        )
    ),
    ui.layout_column_wrap(
        ui.input_slider("P", "Pressure Limits (GPa)", -0.5, 32, [-0.5, 19], step=5e-2),
        ui.input_slider("T", "Temperature Limits (˚C)", 0, T_max, [0, 1650], step=50),
        ui.input_action_button("toggle_reactants", "Select All Reactants"),
        ui.input_action_button("toggle_products", "Select All Products"),
        fill=False
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Phase Diagram"),
            ui.output_plot("visualize_rxns"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Database"),
            ui.output_data_frame("rxns_db"),
            full_screen=True,
        )
    ),
    ui.include_css(app_dir / "styles.css"),
    title="rxnsDB",
    fillable=True
)

def server(input, output, session):
    df = load_data("rxns.csv")

    selected_all_reactants = reactive.value(False)
    selected_all_products = reactive.value(False)

    @reactive.effect
    @reactive.event(input.toggle_reactants)
    def toggle_reactants():
        """
        """
        if selected_all_reactants():
            ui.update_checkbox_group("reactants", selected=init_phases)
        else:
            ui.update_checkbox_group("reactants", selected=phases)
        selected_all_reactants.set(not selected_all_reactants())

        return None

    @reactive.effect
    @reactive.event(input.toggle_products)
    def toggle_products():
        """
        """
        if selected_all_products():
            ui.update_checkbox_group("products", selected=init_phases)
        else:
            ui.update_checkbox_group("products", selected=phases)
        selected_all_products.set(not selected_all_products())

        return None

    @reactive.calc
    def filtered_df():
        """
        """
        filt_df = df[
            (df["reactant1"].isin(input.reactants()) |
             df["reactant2"].isin(input.reactants()) |
             df["reactant3"].isin(input.reactants())) &
            (df["product1"].isin(input.products()) |
             df["product2"].isin(input.products()) |
             df["product3"].isin(input.products()))
        ].copy()
        filt_df = filt_df[~filt_df["id"].isin([45, 73, 74])]
        filt_df = filt_df[filt_df["b"].notna()]

        terms = ["t1", "t2", "t3", "t4", "b"]
        def create_poly(row):
            poly_parts = []
            for i, term in enumerate(terms):
                if term in filt_df.columns and pd.notna(row[term]):
                    if term != "b":
                        if i == 0:
                            poly_parts.append(f"{row[term]}x")
                        else:
                            poly_parts.append(f"{row[term]}x^{i+1}")
                    else:
                        poly_parts.append(f"{row[term]}")
            return "y = " + " + ".join(poly_parts) if poly_parts else "y = 0"

        filt_df["polynomial"] = filt_df.apply(create_poly, axis=1)

        return filt_df

    @render.plot
    def visualize_rxns():
        """
        """
        dark_mode = input.mode() == "dark"
        plt.rcParams.update({
            "font.size": 5,
            "figure.dpi": 300,
            "savefig.bbox": "tight",
            "axes.facecolor": "0.9" if not dark_mode else "0.6",
            "figure.facecolor": "none",
            "legend.frameon": False,
            "legend.facecolor": "0.9" if not dark_mode else "0.1",
            "legend.loc": "upper left",
            "figure.autolayout": True,
            "axes.labelcolor": "white" if dark_mode else "black",
            "axes.titlecolor": "white" if dark_mode else "black",
            "axes.edgecolor": "white" if dark_mode else "black",
            "xtick.color": "white" if dark_mode else "black",
            "ytick.color": "white" if dark_mode else "black",
            "grid.color": "white" if dark_mode else "0.7",
            "grid.linestyle": "-" if dark_mode else "--",
            "grid.linewidth": 0.5,
            "grid.alpha": 0.5,
            "axes.grid": True,
        })

        nsteps = 1e3
        filtered = filtered_df()

        rxn_curves = []
        midpoints = []

        for _, row in filtered.iterrows():
            Ts = np.linspace(row["tmin"], row["tmax"], int(nsteps))
            Ps = row["b"]

            terms = ["t1", "t2", "t3", "t4"]
            for i, term in enumerate(terms, start=1):
                t = row[term]
                if pd.notna(t):
                    Ps += t * Ts**i

            for t, p in zip(Ts, Ps):
                rxn_curves.append({"T (˚C)": t, "P (GPa)": p, "Rxn": row["rxn"],
                                   "id": row["id"]})

            midpoint_T = np.mean(Ts)
            midpoint_P = row["b"]
            for i, term in enumerate(terms, start=1):
                t = row[term]
                if pd.notna(t):
                    midpoint_P += t * midpoint_T**i

            midpoints.append({"T (˚C)": midpoint_T, "P (GPa)": midpoint_P, "Rxn": row["rxn"],
                             "id": row["id"]})

        plot_df = pd.DataFrame(rxn_curves)
        if not plot_df.empty:
            mp_df = pd.DataFrame(midpoints)
            plot_df["id"] = pd.Categorical(plot_df["id"])
            mp_df["id"] = pd.Categorical(mp_df["id"])

            plot_df = plot_df[
                (plot_df["T (˚C)"] >= input.T()[0]) & (plot_df["T (˚C)"] <= input.T()[1]) &
                (plot_df["P (GPa)"] >= input.P()[0]) & (plot_df["P (GPa)"] <= input.P()[1])
            ]

            mp_df = mp_df[
                (mp_df["T (˚C)"] >= input.T()[0]) & (mp_df["T (˚C)"] <= input.T()[1]) &
                (mp_df["P (GPa)"] >= input.P()[0]) & (mp_df["P (GPa)"] <= input.P()[1])
            ]

            sns.lineplot(data=plot_df, x="T (˚C)", y="P (GPa)", linewidth = 0.8, hue="id",
                         hue_order=filtered["id"], legend=False)
            sns.scatterplot(data=mp_df, x="T (˚C)", y="P (GPa)", label="id", linewidth=0.3,
                            edgecolor="black", color="#E5E5E5", s=50, marker="o", zorder=3,
                            legend=False)
            for _, row in mp_df.iterrows():
                plt.text(row["T (˚C)"], row["P (GPa)"], row["id"], fontsize=4, ha="center",
                         va="center", zorder=4)

        else:
            plt.text((input.T()[1]-input.T()[0])/2, (input.P()[1]-input.P()[0])/2,
                     "No Data to Display", fontsize=18, ha="center", va="center")
            plt.xlabel("T (˚C)")
            plt.ylabel("P (GPa)")

        plt.xlim(input.T()[0], input.T()[1])
        plt.ylim(input.P()[0], input.P()[1])
        plt.tight_layout(pad=1)

        return None

    @render.data_frame
    def rxns_db():
        """
        """
        cols = ["id", "formula", "rxn", "polynomial", "ref"]
        return render.DataTable(filtered_df()[cols], height="98%")

app = App(app_ui, server)
