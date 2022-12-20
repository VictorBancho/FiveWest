import pandas as pd
import sys

#Input keyword 'example' reproduces example from assignment sheet.
if sys.argv[1] == 'example':
    data1 = {'Account_name':['Arbitrage', 'Quant', 'Discretionary'],
            'Capital': [1000, 500, 600], 
            'allocation_fraction': [0.476190, 0.238095, 0.285714]}
    old_df = pd.DataFrame(data1).set_index('Account_name')

    data2 = {'Account_name':['Arbitrage', 'Quant', 'Discretionary', 'SEC Fines'],
            'allocation_fraction': [0.3, 0.5, 0.1, 0.1]}
    new_df = pd.DataFrame(data2).set_index('Account_name')

else:   # For input from csv dataframes set index too
    old_df = pd.read_csv(sys.argv[1]).set_index('Account_name')
    new_df = pd.read_csv(sys.argv[2]).set_index('Account_name')

capital = old_df.sum()[0]   # Net amount of capital
N = len(new_df)     # Used for number of loop iterations

# To facilitate easier calculations, make shape of old and new dataframes the same.
new_row = pd.DataFrame({'allocation_fraction':[0]}, index = pd.Index(['SEC Fines'], name = 'Account_name'))
# Append row and then take difference of new and old account dataframes. Drop 'Capital' column, only interested in percentages 
# Working with the differences simpilfies operations. We just want each element to go to zero.
diff = pd.concat([old_df.drop(['Capital'], axis=1), new_row]) - new_df      

transfers = []      # Will store the transfer details

# Function to update the transfers array with the required details
def update(amnt, from_acc, to_acc, transfers_arr):
    transfers_arr.append(f'Send {amnt} from {from_acc} to {to_acc}')

# Iterate through each allocation_fraction. If it is in excess, it has funds which must be reallocated.
for i in range(N):
    if diff['allocation_fraction'][i] > 0:      # Check excess
        # Iterate through each following asset to look for where funds can be reallocated
        for j in range(N):
            if i == j: continue     # Skip self-reference
            elif diff['allocation_fraction'][j] < 0:    # Reallocated funds must go to under-funded assets, hence '< 0'.

                # If reallocation is not enough to remove deficit from the under-funded asset, means all of the excess can be sent
                if diff['allocation_fraction'][i] + diff['allocation_fraction'][j] <= 0:
                    amnt = round(diff['allocation_fraction'][i]*capital,1)      # Get capital amount of excess
                    update(amnt, diff.index.values[i], diff.index.values[j], transfers)     # Update the transfers array
                    diff['allocation_fraction'][j] += diff['allocation_fraction'][i]        # Fund the under-funded asset
                    diff['allocation_fraction'][i] = 0                                      # Remove all excess from over-funded asset
                    break   # i'th asset is balanced. Move on to check next asset
                
                else:   # If reallocation is more than enough to remove deficit, then only allocate enough to remove deficit.
                        # Next looping on j'th index will seek to reduce excess by further reallocation.
                    # Get amount that must be allocated (the negative of the under-funded asset's deficit)
                    amnt = -round(diff['allocation_fraction'][j]*capital,1) 
                    update(amnt, diff.index.values[i], diff.index.values[j], transfers)
                    diff['allocation_fraction'][i] += diff['allocation_fraction'][j]        # Reduce over-funded asset's excess
                    diff['allocation_fraction'][j] = 0                                      # Remove under-funded asset's deficit

print(transfers)