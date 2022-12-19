import pandas as pd
import sys

#Input keyword 'example' followed by '1' or '2' reproduces example from assignment sheet.
if sys.argv[1] == 'example':
    in_df = pd.DataFrame({'MCAP':[20000, 10000, 5000], 'Price':[50,25,10]}, 
                        index = pd.Index(['BTC', 'ETH', 'LTC'], name = 'Ticker'))
    total_capital = 10000
    if sys.argv[2] == '1' : asset_cap = 0.5     #e.g. 1
    else: asset_cap = 0.1                       #e.g. 2

else: 
    in_df = pd.read_csv(sys.argv[1]).set_index('Ticker')     #Set Ticker as index
    asset_cap = float(sys.argv[2])
    total_capital = float(sys.argv[3])

# Sort by descending market cap values, to simplify algorithm - the excess just gets passed one.
in_df = in_df.sort_values(by = 'MCAP', ascending=False)

N = len(in_df)      # Used for number of loop iterations
if asset_cap < 1/N: asset_cap = 1/N     # Ensure realistic asset cap (not lest than minimum)
if asset_cap > 1: asset_cap = 1         # Not greater than 1

netCAP = in_df['MCAP'].sum()            # Total overall market cap
perCAP = (in_df['MCAP']/netCAP)         # Percentage market cap of each ticker

# Initialise output dataframe
out_df = pd.DataFrame(columns=['Amount','USD Value', '%'], index = in_df.index)     

# Iterate from from most weighted asset to least weighted.
# If market cap is exceeded, redistribute with the remaining assets according to their relative market cap proportions.
for i in range(N):
    if perCAP[i] > asset_cap:
        excess = perCAP[i] - asset_cap
        # Get the relative proportions of the remaining assets. Divide each market cap by the new net cap (without asset 'i')
        new_proportions = in_df['MCAP'][i+1:]/in_df['MCAP'][i+1:].sum()
        perCAP[i] = asset_cap   # Update capped asset
        perCAP[i+1:] += new_proportions*excess  # Distribute excess in correct proportion

# Lastly solving for required outputs, formatting data and populating output dataframe
out_df['%'] = round(perCAP*100,4)
out_df['USD Value'] = total_capital*perCAP
out_df['Amount'] = round(out_df['USD Value']/in_df['Price'], 6)
out_df['USD Value'] = round(out_df['USD Value'], 2)

print(out_df)