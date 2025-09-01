import streamlit as st
import json
import pandas as pd

# Hardcode VAT as 20%
VAT_VALUE = 20


def compute_profit_percentage(sell_price, post_cost, cost_price, platform_fee, extra_cost=0):
    """
    Calculate profit percentage using the logic:
      1. SellPriceMinusFee = sell_price * (1 - (platform_fee/100))
      2. SellPriceVAT = (sell_price / 120) * 20
      3. PostCostVAT = post_cost * (VAT_VALUE/100)
      4. CostPriceVAT = cost_price * (VAT_VALUE/100)
      5. TotalVATPaid = PostCostVAT + CostPriceVAT
      6. IncomeAfterFees = SellPriceMinusFee - post_cost
      7. ExtraVATDue = SellPriceVAT - TotalVATPaid
      8. Profit = IncomeAfterFees - (cost_price + CostPriceVAT + ExtraVATDue + extra_cost)
      9. Profit Percentage = Profit / sell_price
    """
    if sell_price == 0:
        return 0.0
    sell_price_minus_fee = sell_price * (1 - (platform_fee / 100))
    sell_price_vat = (sell_price / 120) * 20
    post_cost_vat = post_cost * (VAT_VALUE / 100)
    cost_price_vat = cost_price * (VAT_VALUE / 100)
    total_vat_paid = post_cost_vat + cost_price_vat
    income_after_fees = sell_price_minus_fee - post_cost
    extra_vat_due = sell_price_vat - total_vat_paid
    profit = income_after_fees - (cost_price + cost_price_vat + extra_vat_due + extra_cost)
    profit_percentage = profit / sell_price
    return profit_percentage


def find_selling_price(cost_price, post_cost, platform_fee, target_profit_pct, extra_cost=0):
    """
    Iteratively determine the selling price so that the computed profit percentage
    equals the target profit percentage.
    """
    target_profit_decimal = target_profit_pct / 100.0
    initial_sell_price = (cost_price + post_cost + extra_cost) * (
        1 + (platform_fee / 100) + (VAT_VALUE / 100) + (target_profit_pct / 100)
    )
    sell_price = max(0.0, initial_sell_price)
    tolerance = 0.0001
    max_iterations = 10000

    for _ in range(max_iterations):
        current_profit_pct = compute_profit_percentage(
            sell_price, post_cost, cost_price, platform_fee, extra_cost
        )
        diff = current_profit_pct - target_profit_decimal
        if abs(diff) < tolerance:
            break
        if diff < 0:
            sell_price += 0.01
        else:
            sell_price -= 0.01
            if sell_price < 0:
                sell_price = 0.0
                break

    # Round to 2dp as you'd actually list it, then recompute profit for display
    sell_price = round(sell_price + 1e-9, 2)
    return sell_price, compute_profit_percentage(
        sell_price, post_cost, cost_price, platform_fee, extra_cost
    )


@st.cache_data
def load_config(config_file="config.json"):
    """
    Loads a JSON configuration file that contains both platform settings and postage options.
    Cached to avoid re-reading on every rerun.
    """
    with open(config_file, "r") as f:
        config = json.load(f)
    platforms = config.get("platforms", {})
    postage_options = config.get("postage_options", {})
    return platforms, postage_options


def format_postage_options(postage_options, cost_price):
    """
    Returns a dictionary mapping formatted postage option labels to their cost,
    filtering out options where cost_price exceeds the option's max_value.
    Also returns a list of messages for options that were removed.
    """
    available_options = {}
    removed_options = []
    for key, data in postage_options.items():
        cost = data.get("cost")
        max_value = data.get("max_value")
        if max_value is not None and cost_price > max_value:
            removed_options.append(f"{key} (max cost: £{max_value:.2f}) not available")
        else:
            label = f"{key} (Cost: £{cost:.2f})"
            available_options[label] = cost
    return available_options, removed_options


# ---------------- UI HEADER ----------------
st.markdown("<h1 style='text-align:center;'>Pet Connection Repricer</h1>", unsafe_allow_html=True)
st.markdown(
    """
<div style='text-align:center; font-size:18px;'>
This tool calculates the required selling price to achieve a desired profit percentage for each platform.
Platform-specific settings and postage options are loaded from a configuration file.
When calculating for multiples, you can assign a postage choice for each quantity option.
Note: Some postage providers become unavailable if the cost price is too high.
</div>
""",
    unsafe_allow_html=True,
)

# Load configuration (cached).
platforms, postage_options = load_config()

# ---------------- INPUTS (auto-recalculate; no form) ----------------
col1, col2 = st.columns([1, 1])

with col1:
    multiple_mode = st.checkbox(
        "Calculate for multiple quantities?", value=False, key="multiple_mode"
    )

with col2:
    # Robust decimal input for cost price: free-typing string; validate continuously
    if "cost_price_text" not in st.session_state:
        st.session_state.cost_price_text = "0.00"
    cost_price_text = st.text_input(
        "Enter the Cost Price (£):",
        value=st.session_state.cost_price_text,
        key="cost_price_input_text",
        help="Type numbers freely; comma or dot for decimals, up to 2 decimals.",
    )
    st.session_state.cost_price_text = cost_price_text

# Try parse for live UI and calculations
cost_price_valid = True
try:
    cost_price_preview = float(st.session_state.cost_price_text.replace(",", "."))
    if cost_price_preview < 0:
        cost_price_valid = False
        cost_price_preview = 0.0
except Exception:
    cost_price_valid = False
    cost_price_preview = 0.0

# Build postage options from preview value so UI updates while typing
formatted_postage, removed_options = format_postage_options(postage_options, cost_price_preview)

if removed_options:
    removed_str = ", ".join(removed_options)
    st.markdown(
        f"<div style='color:red; text-align:center; font-size:16px;'>"
        f"The following postage options are not available for the entered cost price: {removed_str}"
        f"</div>",
        unsafe_allow_html=True,
    )

# Postage selectors
if not multiple_mode:
    if formatted_postage:
        selected_postage_label = st.selectbox(
            "Select the Postage Type (for single item):",
            list(formatted_postage.keys()),
            key="single_postage_select",
        )
        single_post_cost = formatted_postage.get(selected_postage_label, 0.0)
        st.write(f"Selected Postage Cost: £{single_post_cost:.2f}")
    else:
        st.error("No available postage options for the entered cost price.")
        single_post_cost = 0.0
    max_quantity = None
    postage_by_quantity = None
else:
    if not formatted_postage:
        st.error("No available postage options for the entered cost price. Adjust cost price or config.")
    max_quantity = st.number_input(
        "Enter maximum quantity:",
        min_value=2,
        value=3,
        step=1,
        key="max_quantity_input",
    )
    st.markdown("### Select a Postage Option for Each Quantity Option")
    postage_by_quantity = {}
    options_list = list(formatted_postage.keys())
    default_index = 1 if len(options_list) > 1 else 0
    for q in range(1, int(max_quantity) + 1):
        key_label = f"Select Postage Option for quantity {q}:"
        selected_label = st.selectbox(
            key_label,
            options_list if options_list else ["(no options)"],
            key=f"postage_q_{q}",
            index=default_index if options_list else 0,
        )
        postage_by_quantity[q] = formatted_postage.get(selected_label, 0.0)

# ---------------- RESULTS ----------------
result_container = st.empty()

# If the cost price is not valid yet, show a gentle hint and skip calculations
if not cost_price_valid:
    result_container.info("Enter a valid cost price (e.g., 12.34) to calculate.")
else:
    cost_price = float(st.session_state.cost_price_text.replace(",", "."))

    if not platforms:
        st.error("Platform configuration is missing. Please check your config.json file.")
    else:
        if not multiple_mode:
            results_output = ""
            for platform_name, params in platforms.items():
                fee = params.get("fee", 0.0)
                target_profit_pct_platform = params.get("target_profit_pct", 0.0)
                extra_cost = params.get("extra_cost", 0.0)
                unit_sell_price, unit_profit = find_selling_price(
                    cost_price, single_post_cost, fee, target_profit_pct_platform, extra_cost
                )
                results_output += f"""<div style="text-align:center; font-size:24px;">
<strong>{platform_name}:</strong> Selling Price = <strong style='color:green;'>&pound;{unit_sell_price:.2f}</strong>, Profit = <strong style='color:green;'>{unit_profit:.2%}</strong>
</div><br>"""
            result_container.markdown(results_output, unsafe_allow_html=True)
        else:
            if not formatted_postage:
                st.stop()  # prevent table build when none exist
            for platform_name, params in platforms.items():
                fee = params.get("fee", 0.0)
                target_profit_pct_platform = params.get("target_profit_pct", 0.0)
                extra_cost = params.get("extra_cost", 0.0)
                st.markdown(f"**{platform_name}:**")
                multiple_results = []

                baseline_unit_sell_price, _ = find_selling_price(
                    cost_price, postage_by_quantity.get(1, 0.0), fee, target_profit_pct_platform, extra_cost
                )
                for q in range(1, int(max_quantity) + 1):
                    total_cost = cost_price * q
                    post_cost_q = postage_by_quantity.get(q, 0.0)
                    sell_price_q, profit_q = find_selling_price(
                        total_cost, post_cost_q, fee, target_profit_pct_platform, extra_cost
                    )
                    baseline_total = baseline_unit_sell_price * q
                    discount_amount = baseline_total - sell_price_q
                    discount_pct = (discount_amount / baseline_total * 100) if baseline_total > 0 else 0
                    multiple_results.append(
                        {
                            "Quantity": q,
                            "Profit": f"{profit_q:.2%}",
                            "Baseline Total": f"£{baseline_total:.2f}",
                            "Discount Amount": f"£{discount_amount:.2f}",
                            "Selling Price": f"£{sell_price_q:.2f}",
                            "Discount %": f"{discount_pct:.2f}%",
                        }
                    )
                order = ["Quantity", "Profit", "Baseline Total", "Discount Amount", "Selling Price", "Discount %"]
                df_results = pd.DataFrame(multiple_results)[order]
                raw_table = df_results.to_html(index=False)
                table_html = f"""
                <div style="text-align:center; font-size:18px;">
                <style>
                    table {{ margin: 0 auto; }}
                    table td:nth-child(5), table th:nth-child(5),
                    table td:nth-child(6), table th:nth-child(6) {{
                        color: green;
                        font-weight: bold;
                    }}
                </style>
                {raw_table}
                </div>
                """
                st.markdown(table_html, unsafe_allow_html=True)
