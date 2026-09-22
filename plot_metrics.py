"""
plot_metrics.py
Generates a dual-line graph showing transit delay and playout target window.
"""

import pandas as pd
import matplotlib.pyplot as plt

def main():
    """
    Reads jitter_metrics.csv and plots Transit Delay (n_i) vs Playout Target (p_i).
    """
    try:
        df = pd.read_csv('jitter_metrics.csv')
    except FileNotFoundError:
        print("jitter_metrics.csv not found.")
        return
    except pd.errors.EmptyDataError:
        print("No data in jitter_metrics.csv yet.")
        return

    if df.empty:
        print("No data in jitter_metrics.csv.")
        return

    plt.figure(figsize=(10, 6))

    # Plot Transit Delay (n_i)
    # pylint: disable=line-too-long
    plt.plot(df['seq_num'], df['transit_delay'], label='Transit Delay ($n_i$)', color='blue', alpha=0.6, linewidth=1.5)

    # Plot Playout Target Window (p_i)
    plt.plot(df['seq_num'], df['playout_target'], label='Playout Target Window ($p_i$)', color='red', alpha=0.8, linewidth=2)

    plt.title('VoIP Engine: Adaptive Jitter Management Analysis')
    plt.xlabel('Sequence Number')
    plt.ylabel('Delay (ms)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    plt.show()

if __name__ == "__main__":
    main()
