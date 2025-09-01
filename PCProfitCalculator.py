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
        "Calculate for multiple quantities?", value=
