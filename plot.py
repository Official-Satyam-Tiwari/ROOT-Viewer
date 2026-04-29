import uproot
import matplotlib.pyplot as plt

# Configuration
file_path = "input/prof_confirmation.root"
tree_name = "Singles"
branch_name = "comptonPhantom"
num_events = 100000

# Load data
with uproot.open(file_path) as file:
    tree = file[tree_name]
    data = tree[branch_name].array(library="np", entry_stop=num_events)

# Plotting
plt.figure(figsize=(10, 6))
plt.hist(data, bins=50, color='skyblue', edgecolor='black')
plt.title(f"Histogram of {branch_name} (First {num_events} events)")
plt.xlabel(branch_name)
plt.ylabel("Frequency")
plt.grid(alpha=0.3)
plt.show()
