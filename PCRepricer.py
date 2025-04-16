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
    target_profit_pct is provided as a percentage (e.g., 16) and is compared as a decimal (0.16).
    """
    target_profit_decimal = target_profit_pct / 100.0
    initial_sell_price = (cost_price + post_cost + extra_cost) * (
        1 + (platform_fee / 100) + (VAT_VALUE / 100) + (target_profit_pct / 100)
    )
    sell_price = initial_sell_price
    tolerance = 0.0001
    max_iterations = 10000

    for i in range(max_iterations):
        current_profit_pct = compute_profit_percentage(sell_price, post_cost, cost_price, platform_fee, extra_cost)
        diff = current_profit_pct - target_profit_decimal
        if abs(diff) < tolerance:
            break
        if diff < 0:
            sell_price += 0.01
        else:
            sell_price -= 0.01
    return sell_price, compute_profit_percentage(sell_price, post_cost, cost_price, platform_fee, extra_cost)

def load_config(config_file="config.json"):
    """
    Loads a JSON configuration file that contains both platform settings and postage options.
    """
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        platforms = config.get("platforms", {})
        postage_options = config.get("postage_options", {})
        return platforms, postage_options
    except Exception as e:
        st.error(f"Error loading configuration file: {e}")
        return {}, {}

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

# --- Streamlit UI ---

# Move the "Calculate for multiple quantities?" checkbox above the cost price field.
multiple_mode = st.checkbox("Calculate for multiple quantities?", value=False)

# Center the title.
st.markdown("<h1 style='text-align:center;'>Pet Connection Selling Price Calculator</h1>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align:center; font-size:18px;'>
This tool calculates the required selling price to achieve a desired profit percentage for each platform.
Platform-specific settings and postage options are loaded from a configuration file.
When calculating for multiples, you can assign a postage choice for each quantity option.
Note: Some postage providers become unavailable if the cost price is too high.
</div>
""", unsafe_allow_html=True)

# Common input parameter (default cost price now 0)
cost_price = st.number_input("Enter the Cost Price (£):", min_value=0.0, value=0.0, step=0.01)

# Load configuration.
platforms, postage_options = load_config()
formatted_postage, removed_options = format_postage_options(postage_options, cost_price)

# Display message if any options were removed.
if removed_options:
    st.markdown("<div style='color:red; text-align:center; font-size:16px;'>"
                "The following postage options are not available for the entered cost price: "
                + ", ".join(removed_options)
                + "</div>", unsafe_allow_html=True)

# --- Conditional Postage Selection ---
if not multiple_mode:
    if formatted_postage:
        selected_postage_label = st.selectbox("Select the Postage Type (for single item):", list(formatted_postage.keys()))
        single_post_cost = formatted_postage.get(selected_postage_label, 0)
        st.write(f"Selected Postage Cost: £{single_post_cost:.2f}")
    else:
        st.error("No available postage options for the entered cost price.")
        single_post_cost = 0.0
else:
    single_post_cost = 0.0  # Not used in multiple mode

# --- Multiple Quantities Mode Postage Selection ---
if multiple_mode:
    max_quantity = st.number_input("Enter maximum quantity:", min_value=2, value=3, step=1)
    st.markdown("### Select a Postage Option for Each Quantity Option")
    postage_by_quantity = {}
    options_list = list(formatted_postage.keys())
    default_index = 1 if len(options_list) > 1 else 0  # Default to second option if available.
    for q in range(1, int(max_quantity) + 1):
        key_label = f"Select Postage Option for quantity {q}:"
        selected_label = st.selectbox(key_label, options_list, key=f"postage_q_{q}", index=default_index)
        postage_by_quantity[q] = formatted_postage.get(selected_label, 0)

# Create an empty container for single-item results.
result_container = st.empty()

# --- Calculate and Display Results ---
if platforms:
    if not multiple_mode:
        # Build a simple HTML block for each platform's result.
        results_output = ""
        for platform_name, params in platforms.items():
            fee = params.get("fee", 0)
            target_profit_pct_platform = params.get("target_profit_pct", 0)
            extra_cost = params.get("extra_cost", 0)
            unit_sell_price, unit_profit = find_selling_price(cost_price, single_post_cost, fee, target_profit_pct_platform, extra_cost)
            results_output += f"""<div style="text-align:center; font-size:24px;">
<strong>{platform_name}:</strong> Selling Price = <strong style='color:green;'>&pound;{unit_sell_price:.2f}</strong>, Profit = <strong style='color:green;'>{unit_profit:.2%}</strong>
</div><br>"""
        result_container.markdown(results_output, unsafe_allow_html=True)
    else:
        # In multiple mode, output a table for each platform.
        for platform_name, params in platforms.items():
            fee = params.get("fee", 0)
            target_profit_pct_platform = params.get("target_profit_pct", 0)
            extra_cost = params.get("extra_cost", 0)
            st.markdown(f"**{platform_name}:**")
            multiple_results = []
            # Compute baseline unit selling price using the postage option selected for quantity 1.
            baseline_unit_sell_price, _ = find_selling_price(cost_price, postage_by_quantity.get(1, 0), fee, target_profit_pct_platform, extra_cost)
            for q in range(1, int(max_quantity) + 1):
                total_cost = cost_price * q
                post_cost_q = postage_by_quantity.get(q, 0)
                sell_price_q, profit_q = find_selling_price(total_cost, post_cost_q, fee, target_profit_pct_platform, extra_cost)
                baseline_total = baseline_unit_sell_price * q
                discount_amount = baseline_total - sell_price_q
                discount_pct = (discount_amount / baseline_total * 100) if baseline_total > 0 else 0
                multiple_results.append({
                    "Quantity": q,
                    "Profit": f"{profit_q:.2%}",
                    "Baseline Total": f"£{baseline_total:.2f}",
                    "Discount Amount": f"£{discount_amount:.2f}",
                    "Selling Price": f"£{sell_price_q:.2f}",
                    "Discount %": f"{discount_pct:.2f}%"
                })
            order = ["Quantity", "Profit", "Baseline Total", "Discount Amount", "Selling Price", "Discount %"]
            df_results = pd.DataFrame(multiple_results)[order]
            # Style the last two columns with bold green text using applymap, then convert to HTML without index.
            styled_df = df_results.style.applymap(lambda v: "color: green; font-weight: bold;", subset=["Selling Price", "Discount %"])
            table_html = f'<div style="text-align:center; font-size:18px;">{styled_df.to_html(index=False)}</div>'
            st.markdown(table_html, unsafe_allow_html=True)
else:
    st.error("Platform configuration is missing. Please check your config.json file.")
