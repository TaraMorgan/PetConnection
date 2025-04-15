import streamlit as st
import json

def compute_profit_percentage(sell_price, post_cost, cost_price, platform_fee, vat, extra_cost=0):
    """
    Calculate the profit percentage following the provided logic:
    
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
    
    The target_profit_pct is provided as a percentage (e.g., 16 means 16%)
    and is converted to a decimal (e.g., 0.16) for comparison.
    """
    target_profit_decimal = target_profit_pct / 100.0

    # Initial guess: include extra_cost in the base
    initial_sell_price = (cost_price + post_cost + extra_cost) * (1 + (platform_fee / 100) + (vat / 100) + (target_profit_pct / 100))
    sell_price = initial_sell_price

    tolerance = 0.0001  # acceptable difference in profit percentage (as a decimal)
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

def load_config(config_file="PCConfigs.json"):
    """
    Loads a JSON configuration file that contains platform settings and postage options.
    
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

# --- Streamlit UI ---

st.title("Pet Connection Selling Price Calculator")

st.markdown("""
This tool calculates the required selling price to achieve a desired profit percentage for each platform.
Platform-specific settings (fee, target profit, and extra cost) and postage options are loaded from a configuration file.
""")

# User inputs for common parameters
cost_price = st.number_input("Enter the Cost Price (£):", min_value=0.0, value=8.92, step=0.01)
vat = st.number_input("Enter the VAT (%):", min_value=0.0, value=20.0, step=0.1)

# Load configuration for platforms and postage options
platforms, postage_options = load_config()

# Postage selection: Dropdown of available postage options loaded from config
if postage_options:
    selected_postage = st.selectbox("Select the Postage Type:", list(postage_options.keys()))
    post_cost = postage_options.get(selected_postage, 0)
    st.write(f"Selected Postage Cost for **{selected_postage}**: £{post_cost:.2f}")
else:
    st.error("No postage options found in configuration. Please check your PCConfigs.json file.")
    post_cost = 0.0

if platforms and postage_options:
    st.subheader("Calculated Selling Prices for Each Platform")
    for platform_name, params in platforms.items():
        fee = params.get("fee", 0)
        target_profit_pct = params.get("target_profit_pct", 0)
        extra_cost = params.get("extra_cost", 0)
        sell_price, achieved_profit = find_selling_price(cost_price, post_cost, fee, vat, target_profit_pct, extra_cost)
        st.write(f"**{platform_name}:**")
        st.write("  - Suggested Selling Price: £{:.2f}".format(sell_price))
        st.write("  - Achieved Profit Percentage: {:.2%}".format(achieved_profit))
else:
    st.error("Platform configuration or postage options missing. Please check your PCConfigs.json file.")
