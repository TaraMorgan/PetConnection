import streamlit as st
import json
import pandas as pd

def compute_profit_percentage(sell_price, post_cost, cost_price, platform_fee, vat, extra_cost=0):
    """
    Calculate the profit percentage using the provided logic:
    1. SellPriceMinusFee = sell_price * (1 - (platform_fee/100))
    2. SellPriceVAT = (sell_price / 120) * 20
    3. PostCostVAT = post_cost * (vat/100)
    4. CostPriceVAT = cost_price * (vat/100)
    5. TotalVATPaid = PostCostVAT + CostPriceVAT
    6. IncomeAfterFees = SellPriceMinusFee - post_cost
    7. ExtraVATDue = SellPriceVAT - TotalVATPaid
    8. Profit = IncomeAfterFees - (cost_price + CostPriceVAT + ExtraVATDue + extra_cost)
    9. Profit Percentage = Profit / sell_price
    """
    sell_price_minus_fee = sell_price * (1 - (platform_fee / 100))
    sell_price_vat = (sell_price / 120) * 20
    post_cost_vat = post_cost * (vat / 100)
    cost_price_vat = cost_price * (vat / 100)
    total_vat_paid = post_cost_vat + cost_price_vat
    income_after_fees = sell_price_minus_fee - post_cost
    extra_vat_due = sell_price_vat - total_vat_paid
    profit = income_after_fees - (cost_price + cost_price_vat + extra_vat_due + extra_cost)
    profit_percentage = profit / sell_price
    return profit_percentage

def find_selling_price(cost_price, post_cost, platform_fee, vat, target_profit_pct, extra_cost=0):
    """
    Iteratively determine the selling price so that the computed profit percentage
    equals the target profit percentage.
    target_profit_pct is provided as a percentage (e.g., 16) and is compared as a decimal (0.16).
    """
    target_profit_decimal = target_profit_pct / 100.0
    initial_sell_price = (cost_price + post_cost + extra_cost) * (1 + (platform_fee / 100) + (vat / 100) + (target_profit_pct / 100))
    sell_price = initial_sell_price
    tolerance = 0.0001
    max_iterations = 10000

    for i in range(max_iterations):
        current_profit_pct = compute_profit_percentage(sell_price, post_cost, cost_price, platform_fee, vat, extra_cost)
        diff = current_profit_pct - target_profit_decimal
        if abs(diff) < tolerance:
            break
        if diff < 0:
            sell_price += 0.01
        else:
            sell_price -= 0.01
    return sell_price, compute_profit_percentage(sell_price, post_cost, cost_price, platform_fee, vat, extra_cost)

def load_config(config_file="config.json"):
    """
    Loads a JSON configuration file that contains both platform settings and postage options.
    Expected JSON format:
    {
      "platforms": {
          "Platform A": { "fee": 15, "target_profit_pct": 16, "extra_cost": 0 },
          "Platform B": { "fee": 10, "target_profit_pct": 18, "extra_cost": 0.20 }
      },
      "postage_options": {
          "Large Letter untracked": 1.37,
          "Parcel 48 Tracked": 3.47,
          "DPD GB": 8.07,
          "DPD NI": 5.05,
          "DPD IE": 5.77,
          "Evri 0-2kg": 5.33,
          "Evri 2-5kg": 5.98,
          "Evri 2 - 15kg": 6.09
      }
    }
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

def format_postage_options(postage_options):
    """
    Return a dictionary mapping formatted postage option labels to their cost.
    Example: "Large Letter untracked (Cost: £1.37)" -> 1.37
    """
    formatted = {f"{key} (Cost: £{postage_options[key]:.2f})": postage_options[key]
                 for key in postage_options}
    return formatted

# --- Streamlit UI ---
# Create an empty container at the top for results in single-item mode
result_container = st.empty()

st.title("Pet Connection Selling Price Calculator")

st.markdown("""
This tool calculates the required selling price to achieve a desired profit percentage for each platform.
Platform-specific settings and postage options are loaded from a configuration file.
When calculating for multiples, you can assign a postage choice for each quantity option.
""")

# Common input parameters
cost_price = st.number_input("Enter the Cost Price (£):", min_value=0.0, value=8.92, step=0.01)
vat = st.number_input("Enter the VAT (%):", min_value=0.0, value=20.0, step=0.1)

# Load configuration
platforms, postage_options = load_config()
formatted_postage = format_postage_options(postage_options) if postage_options else {}

# --- Single Item Mode Postage Selection ---
if formatted_postage:
    selected_postage_label = st.selectbox("Select the Postage Type (for single item):", list(formatted_postage.keys()))
    single_post_cost = formatted_postage.get(selected_postage_label, 0)
    st.write(f"Selected Postage Cost: £{single_post_cost:.2f}")
else:
    st.error("No postage options found in configuration.")
    single_post_cost = 0.0

# Option for multiple quantities
multiple_mode = st.checkbox("Calculate for multiple quantities?", value=False)

if multiple_mode:
    max_quantity = st.number_input("Enter maximum quantity:", min_value=2, value=3, step=1)
    st.markdown("### Select a Postage Option for Each Quantity Option")
    postage_by_quantity = {}
    for q in range(1, int(max_quantity) + 1):
        key_label = f"Select Postage Option for quantity {q}:"
        selected_label = st.selectbox(key_label, list(formatted_postage.keys()), key=f"postage_q_{q}")
        postage_by_quantity[q] = formatted_postage.get(selected_label, 0)

# --- Calculate and Display Results ---
if platforms:
    if not multiple_mode:
        # Build a simple HTML block for each platform's result
        results_output = ""
        for platform_name, params in platforms.items():
            fee = params.get("fee", 0)
            target_profit_pct_platform = params.get("target_profit_pct", 0)
            extra_cost = params.get("extra_cost", 0)
            unit_sell_price, unit_profit = find_selling_price(cost_price, single_post_cost, fee, vat, target_profit_pct_platform, extra_cost)
            # Format each line with centered, larger text and bold values.
            results_output += f"""<div style="text-align:center; font-size:24px;">
<strong>{platform_name}:</strong> Selling Price = <strong>£{unit_sell_price:.2f}</strong>, Profit = <strong>{unit_profit:.2%}</strong>
</div><br>"""
        # Display the results at the top using unsafe_allow_html
        result_container.markdown(results_output, unsafe_allow_html=True)
    else:
        # Multiple mode: build a results table for each quantity option.
        for platform_name, params in platforms.items():
            fee = params.get("fee", 0)
            target_profit_pct_platform = params.get("target_profit_pct", 0)
            extra_cost = params.get("extra_cost", 0)
            st.markdown(f"**{platform_name}:**")
            multiple_results = []
            # Also compute baseline single-item unit price for discount calculation.
            unit_sell_price, _ = find_selling_price(cost_price, single_post_cost, fee, vat, target_profit_pct_platform, extra_cost)
            for q in range(1, int(max_quantity) + 1):
                total_cost = cost_price * q
                post_cost_q = postage_by_quantity.get(q, single_post_cost)
                sell_price_q, profit_q = find_selling_price(total_cost, post_cost_q, fee, vat, target_profit_pct_platform, extra_cost)
                baseline_total = unit_sell_price * q
                discount_amount = baseline_total - sell_price_q
                discount_pct = (discount_amount / baseline_total * 100) if baseline_total > 0 else 0
                multiple_results.append({
                    "Quantity": q,
                    "Selling Price": f"£{sell_price_q:.2f}",
                    "Profit": f"{profit_q:.2%}",
                    "Baseline Total": f"£{baseline_total:.2f}",
                    "Discount Amount": f"£{discount_amount:.2f}",
                    "Discount %": f"{discount_pct:.2f}%"
                })
            df_results = pd.DataFrame(multiple_results)
            # Wrap the table HTML in a div to center it and use larger text.
            table_html = f'<div style="text-align:center; font-size:18px;">{df_results.to_html(index=False)}</div>'
            st.markdown(table_html, unsafe_allow_html=True)
else:
    st.error("Platform configuration is missing. Please check your config.json file.")
